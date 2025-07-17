import geopandas as gpd
import os


def open_shapefile(file_path):
    """
    Opens a shapefile and returns a GeoDataFrame.
    """
    try:
        gdf = gpd.read_file(file_path, encoding="euc-kr")
        return gdf
    except Exception as e:
        print(f"❌ Error opening shapefile: {file_path}\n  └ {e}")
        return None


def convert_to_geojson(gdf, original_path, output_folder="geojson_out"):
    """
    Save the GeoDataFrame as a GeoJSON file.
    """
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    base_name = os.path.splitext(os.path.basename(original_path))[0]
    output_path = os.path.join(output_folder, base_name + ".geojson")
    try:
        gdf.to_file(output_path, driver="GeoJSON")
        print(f"✅ Saved to: {output_path}")
    except Exception as e:
        print(f"❌ Failed to save {output_path}: {e}")


def process_all_shapefiles(folder_name):
    """
    Process all .shp files in a folder: open, describe, and export to GeoJSON.
    """
    print("📁 Scanning folder:", folder_name)
    for file in os.listdir(folder_name):
        if file.endswith(".shp"):
            path = os.path.join(folder_name, file)
            print(f"\n📂 Opening shapefile: {path}")
            gdf = open_shapefile(path)
            if gdf is not None and not gdf.empty:
                convert_to_geojson(gdf, path)


# 실행C:\Users\lyy02\Desktop\새 폴더\open_shp.py
if __name__ == "__main__":
    process_all_shapefiles(
        "(B022)국가기본도_읍면동구역경계"
    )  # 원하는 폴더 경로로 수정 가능
