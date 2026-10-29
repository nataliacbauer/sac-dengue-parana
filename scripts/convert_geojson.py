import geopandas as gpd
from shapely.geometry import Point, box
from shapely.ops import unary_union
import shutil
import os

base = r'C:\Natalia\Dengue'
qgis_dir = os.path.join(base, 'data', 'qgis', 'SACDengue 2024')
src_rb = os.path.join(qgis_dir, 'risco_buffer.shp')
src_ab = os.path.join(qgis_dir, 'Abrangencia_estacoes.shp')
src_mu = os.path.join(qgis_dir, '41MUE250GC_SIR.shp')
src_uf = os.path.join(qgis_dir, 'BR_UF_2019.shp')

dst_rb = os.path.join(base, 'web', 'static', 'risco_buffer.geojson')
dst_ab = os.path.join(base, 'web', 'static', 'abrangencia.geojson')
dst_mu = os.path.join(base, 'web', 'static', 'municipios_pr.geojson')
dst_uf = os.path.join(base, 'web', 'static', 'estados_br.geojson')

print("1. Lendo risco_buffer.shp e gerando circulos suaves (quad_segs=64, raio=0.25 graus)...")
gdf_rb = gpd.read_file(src_rb)
smooth_buffers = []
centers = []
for geom in gdf_rb.geometry:
    minx, miny, maxx, maxy = geom.bounds
    cx = (minx + maxx) / 2.0
    cy = (miny + maxy) / 2.0
    centers.append(Point(cx, cy))
    smooth_buffers.append(Point(cx, cy).buffer(0.25, quad_segs=64))

gdf_rb['geometry'] = smooth_buffers
# Salvar backup do shapefile original se ainda nao existir e atualizar shapefile para o QGIS tambem ficar redondo
bak_rb = os.path.join(qgis_dir, 'risco_buffer_orig20seg.shp')
if not os.path.exists(bak_rb):
    gpd.read_file(src_rb).to_file(bak_rb)
gdf_rb.to_file(src_rb)

gdf_rb_wgs = gdf_rb.to_crs(epsg=4326)
gdf_rb_wgs.to_file(dst_rb, driver='GeoJSON')
print(f"risco_buffer.geojson salvo: {os.path.getsize(dst_rb)} bytes")

print("2. Gerando Abrangencia_estacoes suave (quad_segs=64, raio=0.50 graus)...")
gdf_ab = gpd.read_file(src_ab)
smooth_ab = unary_union([pt.buffer(0.50, quad_segs=64) for pt in centers])
gdf_ab['geometry'] = [smooth_ab]
bak_ab = os.path.join(qgis_dir, 'Abrangencia_estacoes_orig20seg.shp')
if not os.path.exists(bak_ab):
    gpd.read_file(src_ab).to_file(bak_ab)
gdf_ab.to_file(src_ab)

gdf_ab_wgs = gdf_ab.to_crs(epsg=4326)
gdf_ab_wgs.to_file(dst_ab, driver='GeoJSON')
print(f"abrangencia.geojson salvo: {os.path.getsize(dst_ab)} bytes")

print("3. Convertendo municipios do Parana com fidelidade geometrica...")
gdf_mu = gpd.read_file(src_mu).to_crs(epsg=4326)
gdf_mu['geometry'] = gdf_mu['geometry'].simplify(0.0006, preserve_topology=True)
gdf_mu[['NM_MUNICIP', 'CD_GEOCMU', 'geometry']].to_file(dst_mu, driver='GeoJSON')
print(f"municipios_pr.geojson salvo: {os.path.getsize(dst_mu)} bytes")

print("4. Convertendo divisoes politicas estaduais (BR_UF_2019)...")
gdf_uf = gpd.read_file(src_uf).to_crs(epsg=4326)
bbox_sul = box(-58.0, -30.0, -44.0, -19.0)
gdf_uf = gdf_uf[gdf_uf.geometry.intersects(bbox_sul)].copy()
gdf_uf['geometry'] = gdf_uf['geometry'].simplify(0.001, preserve_topology=True)
cols_uf = [c for c in ['NM_UF', 'SIGLA_UF', 'CD_UF', 'geometry'] if c in gdf_uf.columns]
gdf_uf[cols_uf].to_file(dst_uf, driver='GeoJSON')
print(f"estados_br.geojson salvo: {os.path.getsize(dst_uf)} bytes")
