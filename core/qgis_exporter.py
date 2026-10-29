import os
import sys
from qgis.core import (
    QgsApplication,
    QgsProject,
    QgsLayoutExporter,
    QgsGraduatedSymbolRenderer,
    QgsRendererRange,
    QgsFillSymbol,
    QgsField
)
from PyQt5.QtCore import QVariant

_QGS_APP = None  # referência global para manter a QgsApplication viva

class QgisMapExporter:
    def __init__(self, qgz_path=None):
        if qgz_path is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            qgz_path = os.path.join(base_dir, "data", "qgis", "SAC Dengue Certo2024.qgz")
        self.qgz_path = qgz_path
        
    def export_map(self, resultados_calculo, periodo_texto, output_image_path, dpi=200):
        """
        Gera o mapa oficial do QGIS em alta resolução (JPEG 200 DPI).
        Parâmetros:
          resultados_calculo: lista de dicts retornados por calcular_todas_estacoes()['resultados']
          periodo_texto: string com as datas formatadas, ex: "De 19/10/2026 a 25/10/2026"
          output_image_path: caminho absoluto do arquivo JPEG de saída
          dpi: resolução em pontos por polegada (default: 200 DPI)
        """
        # Garante inicialização do QGIS (mantida viva durante todo o processo:
        # encerrar com exitQgis() e recriar no mesmo processo derruba o Python)
        global _QGS_APP
        qgs_app = QgsApplication.instance()
        need_exit = False
        if qgs_app is None:
            qgs_app = QgsApplication([], False)
            qgs_app.initQgis()
            _QGS_APP = qgs_app
            
        try:
            project = QgsProject.instance()
            project.clear()
            if not project.read(self.qgz_path):
                raise RuntimeError(f"Falha ao carregar projeto QGIS em: {self.qgz_path}")
                
            layers = project.mapLayersByName("risco_buffer")
            if not layers:
                raise RuntimeError("Camada 'risco_buffer' não encontrada no projeto QGIS!")
            rb_layer = layers[0]
            
            # Indexar resultados por cod_ibge
            res_by_ibge = {item['cod_ibge']: item for item in resultados_calculo}
            
            # Adicionar / atualizar campo calc_k177
            rb_layer.startEditing()
            idx_k = rb_layer.fields().indexOf("calc_k177")
            if idx_k == -1:
                rb_layer.addAttribute(QgsField("calc_k177", QVariant.Double))
                rb_layer.updateFields()
                idx_k = rb_layer.fields().indexOf("calc_k177")
                
            for feat in rb_layer.getFeatures():
                cod = feat["cod_IBGE"]
                data = res_by_ibge.get(cod)
                if data and data.get("status") == "OK" and data.get("k177") is not None:
                    rb_layer.changeAttributeValue(feat.id(), idx_k, float(data["k177"]))
                else:
                    # Valor nulo para cair na faixa não analisada
                    rb_layer.changeAttributeValue(feat.id(), idx_k, -9999.0)
                    
            rb_layer.commitChanges()
            
            # Função para criar símbolos com opacidade de 50%
            def make_symbol(hex_color):
                sym = QgsFillSymbol.createSimple({
                    'color': hex_color,
                    'outline_color': '80,80,80,255',
                    'outline_width': '0.2',
                    'outline_style': 'solid'
                })
                sym.setOpacity(0.55)
                return sym
                
            ranges = [
                QgsRendererRange(-10000.0, -5001.0, make_symbol('#d3d3d3'), 'Municípios não Analisados'),
                QgsRendererRange(-5000.0, -501.0, make_symbol('#fff8bd'), 'Risco Baixo'),
                QgsRendererRange(-501.0, 0.0, make_symbol('#ffd95b'), 'Risco Médio'),
                QgsRendererRange(0.0, 624.0, make_symbol('#f15b1b'), 'Risco Alto'),
                QgsRendererRange(624.0, 5000.0, make_symbol('#b50000'), 'Risco Muito Alto')
            ]
            
            renderer = QgsGraduatedSymbolRenderer('calc_k177', ranges)
            rb_layer.setRenderer(renderer)
            rb_layer.triggerRepaint()
            
            # Atualizar Título no Layout oficial
            layout = project.layoutManager().layoutByName("layout sac dengue")
            if not layout:
                raise RuntimeError("Layout 'layout sac dengue' não encontrado no projeto!")
                
            for item in layout.items():
                if hasattr(item, 'text') and 'Risco Climático da Dengue' in item.text():
                    novo_titulo = (
                        "Risco Climático da Dengue por Municípios no Estado do Paraná\n"
                        f"({periodo_texto})"
                    )
                    item.setText(novo_titulo)
                    
            os.makedirs(os.path.dirname(output_image_path), exist_ok=True)
            
            exporter = QgsLayoutExporter(layout)
            settings = QgsLayoutExporter.ImageExportSettings()
            settings.dpi = dpi
            
            # Remover arquivo anterior se existir para evitar erro do driver JPEG
            if os.path.exists(output_image_path):
                try:
                    os.remove(output_image_path)
                except Exception:
                    pass
                    
            result = exporter.exportToImage(output_image_path, settings)
            if result != QgsLayoutExporter.ExportResult.Success:
                raise RuntimeError(f"Erro na exportação QGIS. Código de retorno: {result}")
                
            return output_image_path
        finally:
            if need_exit:
                qgs_app.exitQgis()
