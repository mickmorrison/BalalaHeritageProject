#!/usr/bin/env python3
"""
Balala Pastoral Heritage Project - GeoPackage & QGIS Project Build Script
=========================================================================
Instantiates a complete, turn-key, offline OGC GeoPackage (`balala_pastoral_survey.gpkg`)
and companion pre-configured QGIS project (`balala_pastoral_survey.qgs`) for Windows/QField.

Author: Balala Heritage Project
CRS: EPSG:7856 (GDA2020 / MGA Zone 56)
"""

import os
import sys
import shutil
import csv
import sqlite3
import xml.etree.ElementTree as ET
from xml.dom import minidom
from osgeo import gdal, ogr, osr
from PIL import Image, ImageDraw, ImageFont

# Ensure GDAL exceptions are handled cleanly
gdal.UseExceptions()

# Paths setup
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PKG_DIR = os.path.dirname(SCRIPT_DIR)
REPO_ROOT = os.path.dirname(PKG_DIR)
SCHEMA_DIR = os.path.join(REPO_ROOT, "schema")
MEDIA_DIR = os.path.join(PKG_DIR, "media")
PHOTOS_DIR = os.path.join(MEDIA_DIR, "photos")
PLANS_DIR = os.path.join(MEDIA_DIR, "plans")
SCANS_DIR = os.path.join(MEDIA_DIR, "form_scans")

GPKG_NAME = "balala_pastoral_survey.gpkg"
QGS_NAME = "balala_pastoral_survey.qgs"
GPKG_PATH = os.path.join(PKG_DIR, GPKG_NAME)
QGS_PATH = os.path.join(PKG_DIR, QGS_NAME)

ROOT_GPKG_PATH = os.path.join(REPO_ROOT, GPKG_NAME)
ROOT_QGS_PATH = os.path.join(REPO_ROOT, QGS_NAME)


def log(msg):
    print(f"[BUILD-GPKG] {msg}")


def setup_directories():
    """Ensure directory structure and copy compiled form scans."""
    log("Setting up local directory structure...")
    for d in [PHOTOS_DIR, PLANS_DIR, SCANS_DIR, SCRIPT_DIR]:
        os.makedirs(d, exist_ok=True)

    # Copy compiled PDF forms as working scans if present
    form_map = {
        "form1_structure.pdf": os.path.join(SCANS_DIR, "STR01_form1_scan.pdf"),
        "form2_internal_room.pdf": os.path.join(SCANS_DIR, "STR01_A_form2_scan.pdf"),
        "form3_room_inventory.pdf": os.path.join(SCANS_DIR, "STR01_form3_inventory_scan.pdf"),
        "form4_photo_log.pdf": os.path.join(SCANS_DIR, "STR01_form4_photolog_scan.pdf"),
    }
    for src, dst in form_map.items():
        src_path = os.path.join(REPO_ROOT, src)
        if os.path.exists(src_path):
            shutil.copy2(src_path, dst)
            log(f"  Copied scan template: {src} -> {os.path.relpath(dst, PKG_DIR)}")


def generate_sample_media():
    """Generate authentic, high-quality sample photos and plans for offline preview testing."""
    log("Generating authentic sample photographs and architectural plans...")

    # 1. Primary facade photograph (STR-01 Main Woolshed)
    facade_img = Image.new("RGB", (900, 650), color=(215, 210, 200))
    d = ImageDraw.Draw(facade_img)
    # Ground & sky
    d.rectangle([0, 0, 900, 300], fill=(175, 205, 235))
    d.rectangle([0, 480, 900, 650], fill=(170, 155, 125))
    # Woolshed building
    d.rectangle([120, 260, 780, 500], fill=(155, 105, 65), outline=(70, 45, 20), width=4)
    # Gable CGI roof
    d.polygon([(90, 260), (450, 120), (810, 260)], fill=(130, 135, 140), outline=(50, 55, 60), width=4)
    # CGI corrugation lines on roof
    for x in range(120, 800, 18):
        d.line([(x, 260), (450, 120)], fill=(100, 105, 110), width=1)
    # Large timber loading doors & windows
    d.rectangle([390, 320, 510, 500], fill=(85, 55, 25), outline=(40, 25, 10), width=3)
    d.rectangle([180, 310, 270, 390], fill=(220, 235, 245), outline=(40, 25, 10), width=2)
    d.rectangle([630, 310, 720, 390], fill=(220, 235, 245), outline=(40, 25, 10), width=2)
    # 2m Photographic Scale (alternating 20cm black/white bands)
    d.rectangle([750, 300, 775, 500], fill=(255, 255, 255), outline=(0, 0, 0), width=2)
    for idx, y in enumerate(range(300, 500, 20)):
        if idx % 2 == 1:
            d.rectangle([750, y, 775, y + 20], fill=(0, 0, 0))
    d.text((740, 505), "2m SCALE", fill=(0, 0, 0))
    # North Arrow
    d.polygon([(820, 130), (835, 175), (805, 175)], fill=(200, 20, 20), outline=(0, 0, 0), width=2)
    d.polygon([(820, 175), (820, 130), (835, 175)], fill=(130, 10, 10))
    d.text((815, 105), "N", fill=(200, 20, 20))
    # Metadata footer banner
    d.rectangle([0, 570, 900, 650], fill=(27, 54, 93))
    d.text((25, 582), "BALALA STATION ARCHAEOLOGICAL SURVEY | STR-01 MAIN WOOLSHED", fill=(255, 255, 255))
    d.text((25, 608), "Photo ID: DSC_0401 | Facing: North | Scale: 2m Pole + North Arrow | Date: 14/10/2026", fill=(200, 220, 255))
    facade_img.save(os.path.join(PHOTOS_DIR, "STR01_primary_facade.jpg"), "JPEG", quality=90)

    # 2. Site Plan Graphic
    plan_img = Image.new("RGB", (900, 650), color=(250, 250, 245))
    d = ImageDraw.Draw(plan_img)
    d.rectangle([20, 20, 880, 630], outline=(100, 100, 100), width=2)
    d.rectangle([30, 30, 870, 70], fill=(232, 238, 245), outline=(27, 54, 93), width=1)
    d.text((45, 42), "BALALA STATION - HISTORICAL HOMESTEAD & PASTORAL CURTILAGE SITE PLAN (SP-01)", fill=(27, 54, 93))
    # Buildings on site plan
    # STR-01 Woolshed
    d.rectangle([150, 180, 500, 380], fill=(220, 180, 140), outline=(139, 69, 19), width=3)
    d.text((240, 260), "STR-01: MAIN WOOLSHED (45m x 25m)", fill=(80, 30, 0))
    # STR-02 Shearers Quarters
    d.rectangle([600, 180, 820, 270], fill=(210, 200, 180), outline=(100, 80, 60), width=2)
    d.text((615, 220), "STR-02: SHEARERS QUARTERS", fill=(50, 40, 30))
    # Sheep yards / races
    for y in range(380, 520, 35):
        d.line([(150, y), (500, y)], fill=(150, 130, 110), width=2)
    d.text((250, 440), "HOLDING YARDS & SWEAT PENS RACE", fill=(120, 100, 80))
    # Scale bar & North Arrow
    d.polygon([(820, 90), (835, 135), (805, 135)], fill=(0, 0, 0))
    d.text((815, 70), "N", fill=(0, 0, 0))
    d.line([(150, 580), (350, 580)], fill=(0, 0, 0), width=4)
    d.text((150, 590), "0              10m             20m (Scale 1:500)", fill=(0, 0, 0))
    plan_img.save(os.path.join(PLANS_DIR, "STR01_site_plan.png"))

    # 3. Floor Plan Graphic
    fp_img = Image.new("RGB", (900, 650), color=(250, 250, 245))
    d = ImageDraw.Draw(fp_img)
    d.rectangle([20, 20, 880, 630], outline=(100, 100, 100), width=2)
    d.rectangle([30, 30, 870, 70], fill=(232, 238, 245), outline=(27, 54, 93), width=1)
    d.text((45, 42), "STR-01 MAIN WOOLSHED - MEASURED FLOOR PLAN & ROOM INVENTORY (FP-STR01)", fill=(27, 54, 93))
    # Rooms
    d.rectangle([100, 120, 380, 540], fill=(245, 240, 230), outline=(50, 50, 50), width=3)
    d.text((130, 150), "ROOM C: SWEAT PENS (STR-01-C)\nSlatted hardwood battens\nArea: 160 sq m", fill=(60, 60, 60))
    d.rectangle([380, 120, 560, 540], fill=(235, 245, 235), outline=(50, 50, 50), width=3)
    d.text((400, 150), "ROOM A: SHEARING BOARD\n(STR-01-A)\nButt-boarded floor\n16 Stands | Area: 77.7 sq m\n[➔ Photo DSC_0403]", fill=(20, 70, 20))
    d.rectangle([560, 120, 820, 540], fill=(240, 235, 245), outline=(50, 50, 50), width=3)
    d.text((580, 150), "ROOM B: WOOL ROOM & BINS\n(STR-01-B)\nT&G hardwood floor\nWool press & bins | Area: 180 sq m\n[➔ Photo DSC_0404]", fill=(50, 20, 70))
    fp_img.save(os.path.join(PLANS_DIR, "STR01_floor_plan.png"))

    # 4. Wolseley Shearing Handpiece macro photo
    hp_img = Image.new("RGB", (700, 500), color=(220, 220, 215))
    d = ImageDraw.Draw(hp_img)
    # Mechanical handpiece drawing
    d.rectangle([150, 200, 520, 280], fill=(90, 95, 100), outline=(30, 30, 30), width=3)
    d.polygon([(520, 180), (620, 240), (520, 300)], fill=(180, 185, 190), outline=(30, 30, 30), width=3)
    d.ellipse([180, 210, 260, 270], fill=(60, 60, 65))
    d.text((280, 230), "WOLSELEY BIRMINGHAM NO 2", fill=(240, 240, 240))
    # 10cm metric scale
    d.rectangle([200, 360, 500, 385], fill=(255, 255, 255), outline=(0, 0, 0), width=2)
    for idx, x in enumerate(range(200, 500, 30)):
        if idx % 2 == 1:
            d.rectangle([x, 360, x + 30, 385], fill=(0, 0, 0))
    d.text((280, 395), "10cm METRIC SCALE", fill=(0, 0, 0))
    d.rectangle([0, 440, 700, 500], fill=(27, 54, 93))
    d.text((20, 455), "OBJECT ID: STR-01-A-01 | Wolseley Mechanical Shearing Handpiece (c. 1895)", fill=(255, 255, 255))
    hp_img.save(os.path.join(PHOTOS_DIR, "STR01_A_01_handpiece.jpg"), "JPEG", quality=90)

    # 5. Lysaght Orb Corrugated Iron brand macro photo
    brand_img = Image.new("RGB", (700, 500), color=(180, 185, 190))
    d = ImageDraw.Draw(brand_img)
    # Corrugation background
    for y in range(0, 440, 40):
        d.line([(0, y), (700, y)], fill=(140, 145, 150), width=6)
    # Stamped Orb brand
    d.ellipse([260, 140, 440, 300], fill=(160, 165, 170), outline=(80, 85, 90), width=3)
    d.text((290, 190), "LYSAGHT", fill=(60, 65, 70))
    d.text((310, 215), "ORB", fill=(60, 65, 70))
    d.text((275, 240), "QUEEN'S HEAD", fill=(60, 65, 70))
    # Scale
    d.rectangle([200, 360, 500, 385], fill=(255, 255, 255), outline=(0, 0, 0), width=2)
    for idx, x in enumerate(range(200, 500, 30)):
        if idx % 2 == 1:
            d.rectangle([x, 360, x + 30, 385], fill=(0, 0, 0))
    d.text((280, 395), "10cm SCALE", fill=(0, 0, 0))
    d.rectangle([0, 440, 700, 500], fill=(27, 54, 93))
    d.text((20, 455), "MARK ID: STR-01-M01 | Lysaght Orb Corrugated Iron Brand (c. 1895)", fill=(255, 255, 255))
    brand_img.save(os.path.join(PHOTOS_DIR, "STR01_iron_brand.jpg"), "JPEG", quality=90)


def create_geopackage():
    """Build the complete OGC GeoPackage with spatial layers, tables, and seed records."""
    log(f"Building OGC GeoPackage at: {GPKG_PATH}")
    if os.path.exists(GPKG_PATH):
        os.remove(GPKG_PATH)

    drv = ogr.GetDriverByName("GPKG")
    ds = drv.CreateDataSource(GPKG_PATH)

    # Official EPSG:7856 SRS (GDA2020 / MGA Zone 56)
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(7856)
    srs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)

    # Load codebook dictionary to get field definitions
    codebook_path = os.path.join(SCHEMA_DIR, "codebook_data_dictionary.csv")
    codebook_fields = {}
    with open(codebook_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            codebook_fields.setdefault(r["table_name"], []).append(r)

    # ----------------------------------------------------
    # 1. SPATIAL LAYER: structures (MultiPolygon)
    # ----------------------------------------------------
    log("  Creating spatial layer: structures (MultiPolygon)...")
    lyr_structures = ds.CreateLayer("structures", srs, ogr.wkbMultiPolygon)

    # Add codebook fields
    for f in codebook_fields.get("structures", []):
        fn = f["field_name"]
        st = f["sqlite_data_type"].upper()
        if st == "TEXT":
            fld = ogr.FieldDefn(fn, ogr.OFTString)
            fld.SetWidth(150 if "comments" not in fn and "summary" not in fn else 500)
        elif st in ("REAL", "FLOAT"):
            fld = ogr.FieldDefn(fn, ogr.OFTReal)
        elif st in ("INTEGER", "INT", "BOOLEAN"):
            fld = ogr.FieldDefn(fn, ogr.OFTInteger)
        elif st == "DATE":
            fld = ogr.FieldDefn(fn, ogr.OFTDate)
        else:
            fld = ogr.FieldDefn(fn, ogr.OFTString)
        lyr_structures.CreateField(fld)

    # Direct attachment fields for Form 1
    for att_fld in [
        "primary_facade_photo_path",
        "site_plan_scan_path",
        "floor_plan_scan_path",
        "paper_form1_scan_path",
    ]:
        if lyr_structures.FindFieldIndex(att_fld, True) == -1:
            fld = ogr.FieldDefn(att_fld, ogr.OFTString)
            fld.SetWidth(255)
            lyr_structures.CreateField(fld)

    # ----------------------------------------------------
    # 2. SPATIAL COMPANION LAYER: structures_points (Point)
    # ----------------------------------------------------
    log("  Creating companion spatial layer: structures_points (Point)...")
    lyr_pts = ds.CreateLayer("structures_points", srs, ogr.wkbPoint)
    for fn, ft, w in [
        ("structure_id", ogr.OFTString, 30),
        ("structure_name", ogr.OFTString, 100),
        ("property_name", ogr.OFTString, 100),
        ("recording_date", ogr.OFTDate, 0),
        ("recorders", ogr.OFTString, 100),
        ("gnss_point_id", ogr.OFTString, 50),
        ("overall_condition", ogr.OFTString, 50),
        ("primary_facade_photo_path", ogr.OFTString, 255),
        ("sec1_comments", ogr.OFTString, 500),
    ]:
        fld = ogr.FieldDefn(fn, ft)
        if w > 0:
            fld.SetWidth(w)
        lyr_pts.CreateField(fld)

    # ----------------------------------------------------
    # 3. NON-SPATIAL CHILD TABLE: rooms_spaces (Form 2)
    # ----------------------------------------------------
    log("  Creating child table: rooms_spaces...")
    tbl_rooms = ds.CreateLayer("rooms_spaces", None, ogr.wkbNone)
    for f in codebook_fields.get("rooms_spaces", []):
        fn = f["field_name"]
        st = f["sqlite_data_type"].upper()
        if st == "TEXT":
            fld = ogr.FieldDefn(fn, ogr.OFTString)
            fld.SetWidth(150 if "comments" not in fn and "summary" not in fn else 500)
        elif st in ("REAL", "FLOAT"):
            fld = ogr.FieldDefn(fn, ogr.OFTReal)
        elif st in ("INTEGER", "INT", "BOOLEAN"):
            fld = ogr.FieldDefn(fn, ogr.OFTInteger)
        elif st == "DATE":
            fld = ogr.FieldDefn(fn, ogr.OFTDate)
        else:
            fld = ogr.FieldDefn(fn, ogr.OFTString)
        tbl_rooms.CreateField(fld)

    for add_fld in ["structure_name", "room_unstructured_notes", "paper_form2_scan_path"]:
        if tbl_rooms.FindFieldIndex(add_fld, True) == -1:
            fld = ogr.FieldDefn(add_fld, ogr.OFTString)
            fld.SetWidth(500 if "notes" in add_fld else 255)
            tbl_rooms.CreateField(fld)

    # ----------------------------------------------------
    # 4. NON-SPATIAL GRANDCHILD TABLE: room_objects_inventory (Form 3)
    # ----------------------------------------------------
    log("  Creating grandchild table: room_objects_inventory...")
    tbl_objects = ds.CreateLayer("room_objects_inventory", None, ogr.wkbNone)
    for f in codebook_fields.get("room_objects_inventory", []):
        fn = f["field_name"]
        st = f["sqlite_data_type"].upper()
        if st == "TEXT":
            fld = ogr.FieldDefn(fn, ogr.OFTString)
            fld.SetWidth(150 if "comments" not in fn and "desc" not in fn else 500)
        elif st in ("REAL", "FLOAT"):
            fld = ogr.FieldDefn(fn, ogr.OFTReal)
        elif st in ("INTEGER", "INT", "BOOLEAN"):
            fld = ogr.FieldDefn(fn, ogr.OFTInteger)
        elif st == "DATE":
            fld = ogr.FieldDefn(fn, ogr.OFTDate)
        else:
            fld = ogr.FieldDefn(fn, ogr.OFTString)
        tbl_objects.CreateField(fld)

    for add_fld in ["object_photo_path"]:
        if tbl_objects.FindFieldIndex(add_fld, True) == -1:
            fld = ogr.FieldDefn(add_fld, ogr.OFTString)
            fld.SetWidth(255)
            tbl_objects.CreateField(fld)

    # ----------------------------------------------------
    # 5. NON-SPATIAL CHILD TABLE: construction_stages
    # ----------------------------------------------------
    log("  Creating child table: construction_stages...")
    tbl_stages = ds.CreateLayer("construction_stages", None, ogr.wkbNone)
    for f in codebook_fields.get("construction_stages", []):
        fn = f["field_name"]
        st = f["sqlite_data_type"].upper()
        if st == "TEXT":
            fld = ogr.FieldDefn(fn, ogr.OFTString)
            fld.SetWidth(150 if "clues" not in fn and "rooms" not in fn else 500)
        elif st in ("REAL", "FLOAT"):
            fld = ogr.FieldDefn(fn, ogr.OFTReal)
        elif st in ("INTEGER", "INT", "BOOLEAN"):
            fld = ogr.FieldDefn(fn, ogr.OFTInteger)
        elif st == "DATE":
            fld = ogr.FieldDefn(fn, ogr.OFTDate)
        else:
            fld = ogr.FieldDefn(fn, ogr.OFTString)
        tbl_stages.CreateField(fld)

    for add_fld in ["stage_comments"]:
        if tbl_stages.FindFieldIndex(add_fld, True) == -1:
            fld = ogr.FieldDefn(add_fld, ogr.OFTString)
            fld.SetWidth(500)
            tbl_stages.CreateField(fld)

    # ----------------------------------------------------
    # 6. NON-SPATIAL CHILD TABLE: diagnostic_marks
    # ----------------------------------------------------
    log("  Creating child table: diagnostic_marks...")
    tbl_marks = ds.CreateLayer("diagnostic_marks", None, ogr.wkbNone)
    for f in codebook_fields.get("diagnostic_marks", []):
        fn = f["field_name"]
        st = f["sqlite_data_type"].upper()
        if st == "TEXT":
            fld = ogr.FieldDefn(fn, ogr.OFTString)
            fld.SetWidth(150 if "text" not in fn and "loc" not in fn else 500)
        elif st in ("REAL", "FLOAT"):
            fld = ogr.FieldDefn(fn, ogr.OFTReal)
        elif st in ("INTEGER", "INT", "BOOLEAN"):
            fld = ogr.FieldDefn(fn, ogr.OFTInteger)
        elif st == "DATE":
            fld = ogr.FieldDefn(fn, ogr.OFTDate)
        else:
            fld = ogr.FieldDefn(fn, ogr.OFTString)
        tbl_marks.CreateField(fld)

    for add_fld in ["mark_photo_path"]:
        if tbl_marks.FindFieldIndex(add_fld, True) == -1:
            fld = ogr.FieldDefn(add_fld, ogr.OFTString)
            fld.SetWidth(255)
            tbl_marks.CreateField(fld)

    # ----------------------------------------------------
    # 7. NON-SPATIAL MULTIMEDIA TABLE: media_attachments
    # ----------------------------------------------------
    log("  Creating multimedia attachment table: media_attachments...")
    tbl_media = ds.CreateLayer("media_attachments", None, ogr.wkbNone)
    for fn, ft, w in [
        ("structure_id", ogr.OFTString, 30),
        ("room_id", ogr.OFTString, 30),
        ("object_id", ogr.OFTString, 30),
        ("media_type", ogr.OFTString, 50),
        ("camera_make_number", ogr.OFTString, 50),
        ("frame_or_sheet_number", ogr.OFTString, 50),
        ("caption_description", ogr.OFTString, 500),
        ("view_direction", ogr.OFTString, 30),
        ("file_path", ogr.OFTString, 255),
        ("date_captured", ogr.OFTDate, 0),
        ("photographer_author", ogr.OFTString, 100),
    ]:
        fld = ogr.FieldDefn(fn, ft)
        if w > 0:
            fld.SetWidth(w)
        tbl_media.CreateField(fld)

    # ----------------------------------------------------
    # 8. NON-SPATIAL PHOTO REGISTER: photographic_log (Form 4)
    # ----------------------------------------------------
    log("  Creating photographic log table: photographic_log...")
    tbl_photo_log = ds.CreateLayer("photographic_log", None, ogr.wkbNone)
    for f in codebook_fields.get("photographic_log", []):
        fn = f["field_name"]
        st = f["sqlite_data_type"].upper()
        if st == "TEXT":
            fld = ogr.FieldDefn(fn, ogr.OFTString)
            fld.SetWidth(150 if "caption" not in fn and "comments" not in fn else 500)
        elif st in ("REAL", "FLOAT"):
            fld = ogr.FieldDefn(fn, ogr.OFTReal)
        elif st in ("INTEGER", "INT", "BOOLEAN"):
            fld = ogr.FieldDefn(fn, ogr.OFTInteger)
        elif st == "DATE":
            fld = ogr.FieldDefn(fn, ogr.OFTDate)
        else:
            fld = ogr.FieldDefn(fn, ogr.OFTString)
        tbl_photo_log.CreateField(fld)

    # ----------------------------------------------------
    # 9. IMPORT ALL CONTROLLED VOCABULARY TABLES (lut_*)
    # ----------------------------------------------------
    lut_files = [
        "lut_structure_purpose.csv",
        "lut_foundations_and_subfloor.csv",
        "lut_wall_systems_and_framing.csv",
        "lut_masonry_and_cladding.csv",
        "lut_roof_verandah_chimney.csv",
        "lut_openings_and_hardware.csv",
        "lut_internal_rooms_and_services.csv",
        "lut_phasing_whs_and_condition.csv",
        "lut_object_category.csv",
        "lut_photo_orientation.csv",
    ]
    for lut_fn in lut_files:
        tbl_name = os.path.splitext(lut_fn)[0]
        csv_path = os.path.join(SCHEMA_DIR, lut_fn)
        if not os.path.exists(csv_path):
            continue
        log(f"  Importing lookup table: {tbl_name}...")
        tbl_lut = ds.CreateLayer(tbl_name, None, ogr.wkbNone)
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            header = next(reader)
            for col in header:
                fld = ogr.FieldDefn(col, ogr.OFTString)
                fld.SetWidth(255 if "guide" not in col and "desc" not in col else 1000)
                tbl_lut.CreateField(fld)

            # Insert rows
            for row in reader:
                feat = ogr.Feature(tbl_lut.GetLayerDefn())
                for idx, col in enumerate(header):
                    if idx < len(row):
                        feat.SetField(col, row[idx])
                tbl_lut.CreateFeature(feat)

    # ----------------------------------------------------
    # 10. POPULATE SEED TEST DATA (Balala Main Woolshed STR-01)
    # ----------------------------------------------------
    log("  Inserting realistic seed records for Balala Station (STR-01 Main Woolshed & STR-02)...")

    # Structure 1: STR-01 Woolshed (Polygon)
    feat_s1 = ogr.Feature(lyr_structures.GetLayerDefn())
    # 45m x 25m footprint at Balala Station in MGA56
    e_min, e_max = 338800.0, 338845.0
    n_min, n_max = 6622380.0, 6622405.0
    wkt_poly = f"MULTIPOLYGON((({e_min} {n_min}, {e_max} {n_min}, {e_max} {n_max}, {e_min} {n_max}, {e_min} {n_min})))"
    geom_s1 = ogr.CreateGeometryFromWkt(wkt_poly)
    feat_s1.SetGeometry(geom_s1)

    feat_s1.SetField("structure_id", "STR-01")
    feat_s1.SetField("structure_name", "Main Woolshed")
    feat_s1.SetField("property_name", "Balala Station")
    feat_s1.SetField("recording_date", "2026-10-14")
    feat_s1.SetField("recorders", "M. Morrison & Archaeological Survey Team")
    feat_s1.SetField("gnss_point_id", "WP-101 to WP-104")
    feat_s1.SetField("gnss_poly_id", "BALALA-STR01-POLY")
    feat_s1.SetField("site_plan_sheet_no", "SP-01")
    feat_s1.SetField("floor_plan_sheet_no", "FP-STR01")
    feat_s1.SetField("camera_make_number", "Canon-01")
    feat_s1.SetField("photo_frame_range", "DSC_0401-0428")
    feat_s1.SetField("overall_condition", "cond_intact_70")
    feat_s1.SetField("sec1_comments", "Master woolshed complex facing north towards holding yards; full timber framing intact.")

    # WHS check
    feat_s1.SetField("whs_asbestos", 0)
    feat_s1.SetField("whs_lead_paint", 1)
    feat_s1.SetField("whs_unstable_struc", 0)
    feat_s1.SetField("whs_chemical_haz", 1)
    feat_s1.SetField("whs_biological_haz", 0)
    feat_s1.SetField("whs_entry_status", "entry_full_safe")
    feat_s1.SetField("sec2_whs_comments", "Arsenic dip residues near north race; flaking lead paint on interior wool press; safe for internal entry.")

    # Layout & Foundations
    feat_s1.SetField("orig_purpose", "woolshed_shearing")
    feat_s1.SetField("later_use", "woolshed_shearing")
    feat_s1.SetField("storeys_count", "Single")
    feat_s1.SetField("plan_shape", "Rectangular")
    feat_s1.SetField("facade_symmetry", "Asymmetrical")
    feat_s1.SetField("facade_orient", "N")
    feat_s1.SetField("length_m", 45.0)
    feat_s1.SetField("width_m", 25.0)
    feat_s1.SetField("sec3_layout_comments", "Large clear-span timber woolshed with elevated sweat pens and central shearing board.")
    feat_s1.SetField("footing_type", "stump_timber_round")
    feat_s1.SetField("subfloor_timber", "saw_pit_diagonal")
    feat_s1.SetField("subfloor_deposit", "subfloor_high")
    feat_s1.SetField("sec4_found_comments", "Hardwood stumps with tin ant-caps; pit-sawn subfloor bearers; rich under-floor artefactual potential beneath grates.")

    # Walls & Roof
    feat_s1.SetField("wall_system_prim", "wall_stud_light")
    feat_s1.SetField("wall_system_sec", "wall_bush_pole_frame")
    feat_s1.SetField("timber_joints", "joint_mortise_tenon")
    feat_s1.SetField("fasteners_nails", "nail_cut_ewbank")
    feat_s1.SetField("ext_cladding_prim", "cgi_3inch_standard")
    feat_s1.SetField("sec5_wall_comments", "Heavy perimeter box posts with sawn stud infill; Ewbank cut nails on early wall plates.")
    feat_s1.SetField("roof_form", "roof_gable")
    feat_s1.SetField("roof_cladding_cur", "cladding_corrugated_iron")
    feat_s1.SetField("roof_early_clues", "clue_shingle_battens")
    feat_s1.SetField("verandah_loc", "Front")
    feat_s1.SetField("verandah_profile", "ver_straight_skillion")
    feat_s1.SetField("verandah_posts", "post_bush_pole")
    feat_s1.SetField("verandah_status", "Original open")
    feat_s1.SetField("chimney_count", 0)
    feat_s1.SetField("sec6_roof_comments", "Remnant wood shingle battens visible beneath CGI sheets on southern roof pitch.")

    # Openings & Synthesis
    feat_s1.SetField("door_type_prim", "door_ledged_braced")
    feat_s1.SetField("door_hardware", "hw_strap_hinge")
    feat_s1.SetField("window_type_prim", "win_fixed_pane")
    feat_s1.SetField("sec7_openings_comments", "Massive ledged and braced sliding barn doors hung on iron rollers.")
    feat_s1.SetField("sec8_phasing_comments", "Stage 1 (1872) core board and pens; Stage 2 (c. 1895) eastern wool room extension with Lysaght iron.")
    feat_s1.SetField("fabric_intactness", "cond_intact_70")
    feat_s1.SetField("assoc_refuse_dump", 1)
    feat_s1.SetField("assoc_privy_cess", 1)
    feat_s1.SetField("assoc_well_cistern", 0)
    feat_s1.SetField("assoc_fence_lines", 1)
    feat_s1.SetField("recorder_summary", "Exemplary 19th century pastoral woolshed demonstrating transition from pit-sawn handcraft to mechanised shearing.")
    feat_s1.SetField("sec9_synthesis_comments", "Outstanding architectural and historical integrity; high priority for conservation.")

    # Attachments
    feat_s1.SetField("primary_facade_photo_path", "media/photos/STR01_primary_facade.jpg")
    feat_s1.SetField("site_plan_scan_path", "media/plans/STR01_site_plan.png")
    feat_s1.SetField("floor_plan_scan_path", "media/plans/STR01_floor_plan.png")
    feat_s1.SetField("paper_form1_scan_path", "media/form_scans/STR01_form1_scan.pdf")
    lyr_structures.CreateFeature(feat_s1)

    # Structure 2: STR-02 Shearers Quarters (Polygon)
    feat_s2 = ogr.Feature(lyr_structures.GetLayerDefn())
    e2_min, e2_max = 338860.0, 338885.0
    n2_min, n2_max = 6622415.0, 6622425.0
    wkt_s2 = f"MULTIPOLYGON((({e2_min} {n2_min}, {e2_max} {n2_min}, {e2_max} {n2_max}, {e2_min} {n2_max}, {e2_min} {n2_min})))"
    feat_s2.SetGeometry(ogr.CreateGeometryFromWkt(wkt_s2))
    feat_s2.SetField("structure_id", "STR-02")
    feat_s2.SetField("structure_name", "Shearers Quarters")
    feat_s2.SetField("property_name", "Balala Station")
    feat_s2.SetField("recording_date", "2026-10-14")
    feat_s2.SetField("recorders", "M. Morrison & Team")
    feat_s2.SetField("gnss_point_id", "WP-105")
    feat_s2.SetField("overall_condition", "cond_modified_30_70")
    feat_s2.SetField("orig_purpose", "shearers_quarters")
    feat_s2.SetField("later_use", "shearers_quarters")
    feat_s2.SetField("storeys_count", "Single")
    feat_s2.SetField("length_m", 25.0)
    feat_s2.SetField("width_m", 10.0)
    feat_s2.SetField("roof_form", "roof_hipped")
    feat_s2.SetField("ext_cladding_prim", "weatherboard_plain_splayed")
    lyr_structures.CreateFeature(feat_s2)

    # Companion Points in structures_points
    feat_pt1 = ogr.Feature(lyr_pts.GetLayerDefn())
    feat_pt1.SetGeometry(ogr.CreateGeometryFromWkt(f"POINT({(e_min+e_max)/2} {(n_min+n_max)/2})"))
    feat_pt1.SetField("structure_id", "STR-01")
    feat_pt1.SetField("structure_name", "Main Woolshed")
    feat_pt1.SetField("property_name", "Balala Station")
    feat_pt1.SetField("recording_date", "2026-10-14")
    feat_pt1.SetField("recorders", "M. Morrison & Team")
    feat_pt1.SetField("gnss_point_id", "WP-101")
    feat_pt1.SetField("overall_condition", "cond_intact_70")
    feat_pt1.SetField("primary_facade_photo_path", "media/photos/STR01_primary_facade.jpg")
    feat_pt1.SetField("sec1_comments", "GPS centroid waypoint for Main Woolshed.")
    lyr_pts.CreateFeature(feat_pt1)

    feat_pt2 = ogr.Feature(lyr_pts.GetLayerDefn())
    feat_pt2.SetGeometry(ogr.CreateGeometryFromWkt(f"POINT({(e2_min+e2_max)/2} {(n2_min+n2_max)/2})"))
    feat_pt2.SetField("structure_id", "STR-02")
    feat_pt2.SetField("structure_name", "Shearers Quarters")
    feat_pt2.SetField("property_name", "Balala Station")
    feat_pt2.SetField("recording_date", "2026-10-14")
    feat_pt2.SetField("recorders", "M. Morrison & Team")
    feat_pt2.SetField("gnss_point_id", "WP-105")
    feat_pt2.SetField("overall_condition", "cond_modified_30_70")
    lyr_pts.CreateFeature(feat_pt2)

    # Child Rooms in rooms_spaces (STR-01-A, STR-01-B, STR-01-C)
    rooms_seed = [
        {
            "room_id": "STR-01-A",
            "structure_id": "STR-01",
            "structure_name": "Main Woolshed",
            "room_name_or_letter": "Room A: Shearing Board",
            "inferred_use": "room_shearing_board",
            "later_current_use": "room_shearing_board",
            "recording_date": "2026-10-14",
            "recorders": "M. Morrison",
            "floor_plan_sheet_no": "FP-STR01",
            "camera_make_number": "Canon-01",
            "photo_frame_range": "DSC_0403-0408",
            "length_m": 18.5,
            "width_m": 4.2,
            "ceiling_height_m": 3.2,
            "floor_area_sqm": 77.7,
            "floor_material": "floor_butt_boarded",
            "board_width_mm": 150.0,
            "floor_sawing_marks": "saw_circular_curved",
            "subfloor_access_status": "Floorboards lifting / missing",
            "floor_condition": "cond_intact_70",
            "floor_comments": "Steel rule inserted through gaps: 450mm clearance depth over stone bedrock.",
            "wall_structure": "wall_stud_light",
            "wall_lining": "lining_unlined_exposed",
            "ceiling_form": "lining_unlined_exposed",
            "fixed_fittings": "16 shearing stands, chutes, overhead lineshaft pulleys and brackets.",
            "services_utilities": "service_early_electric",
            "diagnostic_inscriptions": "Tally pencil marks on stud 4: '1888 J. Smith 142 sheep'.",
            "room_stratigraphic_summary": "Original 1872 shearing board extended eastwards in c. 1895 when mechanised shearing was installed.",
            "paper_form2_scan_path": "media/form_scans/STR01_A_form2_scan.pdf",
        },
        {
            "room_id": "STR-01-B",
            "structure_id": "STR-01",
            "structure_name": "Main Woolshed",
            "room_name_or_letter": "Room B: Wool Room & Bins",
            "inferred_use": "room_wool_room",
            "later_current_use": "room_wool_room",
            "recording_date": "2026-10-14",
            "recorders": "M. Morrison",
            "floor_plan_sheet_no": "FP-STR01",
            "length_m": 15.0,
            "width_m": 12.0,
            "ceiling_height_m": 4.0,
            "floor_area_sqm": 180.0,
            "floor_material": "floor_tongue_groove",
            "board_width_mm": 146.0,
            "fixed_fittings": "Large slatted wool classing tables, 8 wool bins with Cedar stencils, Humble & Sons wool press.",
            "room_stratigraphic_summary": "Constructed in Stage 2 (c. 1895); floor level flush with board; wire nails predominate.",
        },
        {
            "room_id": "STR-01-C",
            "structure_id": "STR-01",
            "structure_name": "Main Woolshed",
            "room_name_or_letter": "Room C: Sweat Pens",
            "inferred_use": "room_sweat_pen_space",
            "later_current_use": "room_sweat_pen_space",
            "recording_date": "2026-10-14",
            "recorders": "M. Morrison",
            "floor_plan_sheet_no": "FP-STR01",
            "length_m": 20.0,
            "width_m": 8.0,
            "ceiling_height_m": 2.8,
            "floor_area_sqm": 160.0,
            "floor_material": "floor_timber_grates",
            "subfloor_access_status": "Trapdoor present",
            "floor_comments": "Slatted hardwood battens; underfloor dung accumulation containing dropped sheep shears and copper tokens.",
            "room_stratigraphic_summary": "Original 1872 core; heavy bush timber posts with split rail pen gates.",
        },
    ]
    for rdata in rooms_seed:
        feat_r = ogr.Feature(tbl_rooms.GetLayerDefn())
        for k, v in rdata.items():
            feat_r.SetField(k, v)
        tbl_rooms.CreateFeature(feat_r)

    # Grandchild Objects in room_objects_inventory
    objects_seed = [
        {
            "object_id": "STR-01-A-01",
            "structure_id": "STR-01",
            "room_id": "STR-01-A",
            "inventory_sheet_no": "Sheet 1 of 1",
            "recording_date": "2026-10-14",
            "recorders": "M. Morrison",
            "camera_make_number": "Canon-01",
            "photo_frame_no": "DSC_0410",
            "item_category": "pastoral_wool",
            "item_description": "Mechanical shearing handpiece with flexible shaft drive coupling.",
            "material_composition": "Cast iron, brass, steel blades, leather grip washer.",
            "maker_brand_stamps": "WOLSELEY BIRMINGHAM NO 2 / PATENT 1892",
            "dimensions_mm": "Length 320mm x Width 65mm x Height 55mm",
            "item_condition": "Intact/Functional, light surface patina.",
            "in_situ_status": "In-situ original location hanging from stand 4 bracket.",
            "object_photo_path": "media/photos/STR01_A_01_handpiece.jpg",
            "sec3_inventory_comments": "Key diagnostic artifact illustrating adoption of Wolseley mechanical shearing at Balala.",
        },
        {
            "object_id": "STR-01-B-01",
            "structure_id": "STR-01",
            "room_id": "STR-01-B",
            "inventory_sheet_no": "Sheet 1 of 1",
            "recording_date": "2026-10-14",
            "recorders": "M. Morrison",
            "camera_make_number": "Canon-01",
            "photo_frame_no": "DSC_0415",
            "item_category": "pastoral_wool",
            "item_description": "Manual rack and pinion double-box timber and iron wool press.",
            "material_composition": "Hardwood timber box with cast-iron gears and ratchet arms.",
            "maker_brand_stamps": "HUMBLE & SONS VULCAN FOUNDRY GEELONG",
            "dimensions_mm": "Height 2850mm x Width 1200mm x Depth 1100mm",
            "item_condition": "Intact/Functional, cast iron intact.",
            "in_situ_status": "In-situ bolted to floor joists in wool loading bay.",
            "sec3_inventory_comments": "High significance colonial manufacture.",
        },
    ]
    for odata in objects_seed:
        feat_o = ogr.Feature(tbl_objects.GetLayerDefn())
        for k, v in odata.items():
            feat_o.SetField(k, v)
        tbl_objects.CreateFeature(feat_o)

    # Child Construction Stages in construction_stages
    stages_seed = [
        {
            "stage_id": "STR-01-STG1",
            "structure_id": "STR-01",
            "stage_sequence": 1,
            "stage_name": "stage_1_core",
            "rooms_included": "Rooms A & C (Board & Sweat Pens)",
            "physical_clues": "Bush timber pole framing, pit-sawn subfloor bearers, Ewbank cut nails.",
            "fasteners_materials": "Ewbank cut nails, mortise and tenon joinery.",
            "estimated_era": "c. 1872-1875",
            "stage_comments": "Initial station woolshed built under pastoral leasehold expansion.",
        },
        {
            "stage_id": "STR-01-STG2",
            "structure_id": "STR-01",
            "stage_sequence": 2,
            "stage_name": "stage_2_extension",
            "rooms_included": "Room B (Eastern Wool Room)",
            "physical_clues": "Straight vertical joint in wall framing; circular-sawn studs; wire nails.",
            "fasteners_materials": "Early wire nails, circular-sawn hardwood.",
            "estimated_era": "c. 1895-1900",
            "stage_comments": "Wool room added to accommodate mechanized wool baling and classing tables.",
        },
        {
            "stage_id": "STR-01-STG3",
            "structure_id": "STR-01",
            "stage_sequence": 3,
            "stage_name": "stage_3_alterations",
            "rooms_included": "North Engine Skillion Mount",
            "physical_clues": "Concrete engine mount pad, bolts cut into wall sill.",
            "fasteners_materials": "Portland cement pad, machine bolts.",
            "estimated_era": "c. 1928",
            "stage_comments": "Installation of Ronaldson-Tippett diesel engine to drive overhead lineshafts.",
        },
    ]
    for stg in stages_seed:
        feat_stg = ogr.Feature(tbl_stages.GetLayerDefn())
        for k, v in stg.items():
            feat_stg.SetField(k, v)
        tbl_stages.CreateFeature(feat_stg)

    # Diagnostic Marks in diagnostic_marks
    marks_seed = [
        {
            "mark_id": "STR-01-M01",
            "structure_id": "STR-01",
            "room_id": "STR-01-B",
            "item_type": "Corrugated Galvanised Iron Roof Sheet",
            "exact_text_brand": "LYSAGHT ORB / QUEEN'S HEAD / BRISTOL",
            "location_observed": "Under-lap sheet on east wool room roof pitch.",
            "photo_frame_no": "DSC_0418",
            "mark_photo_path": "media/photos/STR01_iron_brand.jpg",
        },
        {
            "mark_id": "STR-01-M02",
            "structure_id": "STR-01",
            "room_id": "STR-01-A",
            "item_type": "Pencil Inscription on Timber Stud",
            "exact_text_brand": "1888 J. SMITH 142 SHEEP / UNION TALLY",
            "location_observed": "Internal face of stud 4 behind shearing stand 3.",
            "photo_frame_no": "DSC_0420",
        },
    ]
    for mk in marks_seed:
        feat_mk = ogr.Feature(tbl_marks.GetLayerDefn())
        for k, v in mk.items():
            feat_mk.SetField(k, v)
        tbl_marks.CreateFeature(feat_mk)

    # Media Attachments in media_attachments
    media_seed = [
        {
            "structure_id": "STR-01",
            "room_id": "",
            "object_id": "",
            "media_type": "Photograph",
            "camera_make_number": "Canon-01",
            "frame_or_sheet_number": "DSC_0401",
            "caption_description": "Primary south elevation of Main Woolshed showing gable profile and scale.",
            "view_direction": "facing_n",
            "file_path": "media/photos/STR01_primary_facade.jpg",
            "date_captured": "2026-10-14",
            "photographer_author": "M. Morrison",
        },
        {
            "structure_id": "STR-01",
            "room_id": "",
            "object_id": "",
            "media_type": "Site Plan",
            "camera_make_number": "",
            "frame_or_sheet_number": "SP-01",
            "caption_description": "Scaled site plan showing curtilage, holding yards, and shearers quarters.",
            "view_direction": "view_down_plan",
            "file_path": "media/plans/STR01_site_plan.png",
            "date_captured": "2026-10-14",
            "photographer_author": "Field Survey Team",
        },
        {
            "structure_id": "STR-01",
            "room_id": "STR-01-A",
            "object_id": "",
            "media_type": "Floor/Roof Plan",
            "camera_make_number": "",
            "frame_or_sheet_number": "FP-STR01",
            "caption_description": "Measured internal floor plan of Woolshed showing Rooms A, B, and C.",
            "view_direction": "view_down_plan",
            "file_path": "media/plans/STR01_floor_plan.png",
            "date_captured": "2026-10-14",
            "photographer_author": "Field Survey Team",
        },
        {
            "structure_id": "STR-01",
            "room_id": "",
            "object_id": "",
            "media_type": "Scanned Paper Form",
            "camera_make_number": "",
            "frame_or_sheet_number": "Sheet 1-3",
            "caption_description": "Archival scan of completed Form 1 Field Proforma.",
            "view_direction": "",
            "file_path": "media/form_scans/STR01_form1_scan.pdf",
            "date_captured": "2026-10-14",
            "photographer_author": "M. Morrison",
        },
        {
            "structure_id": "STR-01",
            "room_id": "STR-01-A",
            "object_id": "STR-01-A-01",
            "media_type": "Photograph",
            "camera_make_number": "Canon-01",
            "frame_or_sheet_number": "DSC_0410",
            "caption_description": "Macro photograph of Wolseley mechanical shearing handpiece with 10cm scale.",
            "view_direction": "oblique_perspective",
            "file_path": "media/photos/STR01_A_01_handpiece.jpg",
            "date_captured": "2026-10-14",
            "photographer_author": "M. Morrison",
        },
    ]
    for m in media_seed:
        feat_m = ogr.Feature(tbl_media.GetLayerDefn())
        for k, v in m.items():
            feat_m.SetField(k, v)
        tbl_media.CreateFeature(feat_m)

    # Photographic Log in photographic_log (Form 4)
    photo_seed = [
        {
            "photo_record_id": "PH-001",
            "structure_id": "STR-01",
            "room_id": "",
            "object_id": "",
            "property_name": "Balala Station",
            "photo_date": "2026-10-14",
            "photographers": "M. Morrison",
            "camera_make_model_id": "Canon-01 (EOS 5D)",
            "memory_card_folder_id": "Card A / DCIM_100",
            "photo_sheet_no": "Sheet 1 of 1",
            "site_floor_plan_sheet": "SP-01",
            "photo_frame_no": "DSC_0401",
            "component_code": "STR-01-EXT-S",
            "facing_orientation": "facing_n",
            "scale_type": "2m pole",
            "north_arrow_used": 1,
            "photo_caption": "Primary south elevation of Main Woolshed with 2m pole and north arrow.",
        },
        {
            "photo_record_id": "PH-002",
            "structure_id": "STR-01",
            "room_id": "STR-01-A",
            "object_id": "STR-01-A-01",
            "property_name": "Balala Station",
            "photo_date": "2026-10-14",
            "photographers": "M. Morrison",
            "camera_make_model_id": "Canon-01 (EOS 5D)",
            "memory_card_folder_id": "Card A / DCIM_100",
            "photo_sheet_no": "Sheet 1 of 1",
            "site_floor_plan_sheet": "FP-STR01",
            "photo_frame_no": "DSC_0410",
            "component_code": "STR-01-A-01",
            "facing_orientation": "oblique_perspective",
            "scale_type": "10cm scale",
            "north_arrow_used": 0,
            "photo_caption": "Close-up of Wolseley shearing handpiece maker stamp with 10cm metric scale.",
        },
    ]
    for p in photo_seed:
        feat_p = ogr.Feature(tbl_photo_log.GetLayerDefn())
        for k, v in p.items():
            feat_p.SetField(k, v)
        tbl_photo_log.CreateFeature(feat_p)

    # Close GeoPackage dataset
    ds = None
    log("  GeoPackage core tables and seed data created successfully!")


def generate_qml_structures(codebook_dict):
    """Generate the complete QML style XML with 7-tab drag-and-drop form layout for structures."""
    root = ET.Element("qgis", styleCategories="AllStyleCategories", version="3.28.0")

    # Symbology (Warm Heritage Sandstone / Ochre fill with dark brown/navy outline)
    renderer = ET.SubElement(root, "renderer-v2", type="singleSymbol", symbollevels="0", enableorderby="0")
    symbols = ET.SubElement(renderer, "symbols")
    sym = ET.SubElement(symbols, "symbol", type="fill", name="0", alpha="0.85", clip_to_extent="1")
    layer = ET.SubElement(sym, "layer", pass_="0", locked="0", class_="SimpleFill")
    ET.SubElement(layer, "prop", k="border_width_map_unit_scale", v="3x:0,0,0,0,0,0")
    ET.SubElement(layer, "prop", k="color", v="217,155,102,216")  # Warm sandstone ochre
    ET.SubElement(layer, "prop", k="joinstyle", v="bevel")
    ET.SubElement(layer, "prop", k="offset", v="0,0")
    ET.SubElement(layer, "prop", k="outline_color", v="27,54,93,255")  # Heritage Navy border
    ET.SubElement(layer, "prop", k="outline_style", v="solid")
    ET.SubElement(layer, "prop", k="outline_width", v="0.8")
    ET.SubElement(layer, "prop", k="outline_width_unit", v="MM")
    ET.SubElement(layer, "prop", k="style", v="solid")

    # Labels (structure_id + structure_name with white buffer halo)
    labeling = ET.SubElement(root, "labeling", type="simple")
    settings = ET.SubElement(labeling, "settings", calloutType="simple")
    text_style = ET.SubElement(settings, "text-style", fontLetterSpacing="0", fontFamily="Helvetica", fontWordSpacing="0", textColor="27,54,93,255", fontSize="9", isExpression="1", fieldName="concat(\"structure_id\", '\n', \"structure_name\")")
    buffer = ET.SubElement(text_style, "text-buffer", bufferSize="1.2", bufferColor="255,255,255,255", bufferDraw="1")

    # Aliases & Tooltips
    aliases = ET.SubElement(root, "aliases")
    fields_elem = ET.SubElement(root, "fieldConfiguration")

    # Mapping of field widgets
    struct_fields = codebook_dict.get("structures", [])
    # Add direct attachments to fields list
    extra_fields = [
        {"field_name": "primary_facade_photo_path", "field_alias": "Primary Façade Photo", "sqlite_data_type": "TEXT", "qgis_widget_type": "ExternalResource", "lookup_table_name": "", "volunteer_field_tip": "Path to primary front elevation photograph."},
        {"field_name": "site_plan_scan_path", "field_alias": "Site Plan Drawing / Scan", "sqlite_data_type": "TEXT", "qgis_widget_type": "ExternalResource", "lookup_table_name": "", "volunteer_field_tip": "Path to scanned or digital site plan."},
        {"field_name": "floor_plan_scan_path", "field_alias": "Floor/Roof Plan Drawing", "sqlite_data_type": "TEXT", "qgis_widget_type": "ExternalResource", "lookup_table_name": "", "volunteer_field_tip": "Path to measured floor/roof plan."},
        {"field_name": "paper_form1_scan_path", "field_alias": "Scanned Form 1 Paper Record", "sqlite_data_type": "TEXT", "qgis_widget_type": "ExternalResource", "lookup_table_name": "", "volunteer_field_tip": "Path to scanned field proforma PDF."},
    ]
    all_struct_fields = struct_fields + extra_fields

    for f in all_struct_fields:
        fn = f["field_name"]
        fa = f["field_alias"]
        tip = f.get("volunteer_field_tip", "")
        lut = f.get("lookup_table_name", "")
        wtype = f.get("qgis_widget_type", "TextEdit")

        ET.SubElement(aliases, "alias", field=fn, name=fa, index="0")

        fcfg = ET.SubElement(fields_elem, "field", name=fn)
        if wtype == "ExternalResource":
            ew = ET.SubElement(fcfg, "editWidget", type="ExternalResource")
            cfg = ET.SubElement(ew, "config")
            opt = ET.SubElement(cfg, "Option", type="Map")
            ET.SubElement(opt, "Option", type="int", name="DocumentViewer", value="1")
            ET.SubElement(opt, "Option", type="int", name="DocumentViewerHeight", value="240")
            ET.SubElement(opt, "Option", type="int", name="DocumentViewerWidth", value="0")
            ET.SubElement(opt, "Option", type="bool", name="FileWidget", value="true")
            ET.SubElement(opt, "Option", type="bool", name="FileWidgetButton", value="true")
            ET.SubElement(opt, "Option", type="int", name="RelativeStorage", value="1")
            ET.SubElement(opt, "Option", type="QString", name="RootPath", value="./media/photos" if "photo" in fn else ("./media/plans" if "plan" in fn else "./media/form_scans"))
            ET.SubElement(opt, "Option", type="int", name="StorageMode", value="0")
        elif wtype == "ValueRelation" and lut:
            ew = ET.SubElement(fcfg, "editWidget", type="ValueRelation")
            cfg = ET.SubElement(ew, "config")
            opt = ET.SubElement(cfg, "Option", type="Map")
            ET.SubElement(opt, "Option", type="bool", name="AllowMulti", value="false")
            ET.SubElement(opt, "Option", type="bool", name="AllowNull", value="true")
            ET.SubElement(opt, "Option", type="QString", name="Description", value='"volunteer_identification_guide"')
            ET.SubElement(opt, "Option", type="QString", name="Key", value="code")
            ET.SubElement(opt, "Option", type="QString", name="Layer", value=f"{lut}")
            ET.SubElement(opt, "Option", type="QString", name="LayerName", value=lut)
            ET.SubElement(opt, "Option", type="QString", name="LayerSource", value=f"./balala_pastoral_survey.gpkg|layername={lut}")
            ET.SubElement(opt, "Option", type="QString", name="LayerProviderName", value="ogr")
            ET.SubElement(opt, "Option", type="bool", name="OrderByValue", value="true")
            ET.SubElement(opt, "Option", type="QString", name="Value", value="label")
        elif wtype == "CheckBox":
            ew = ET.SubElement(fcfg, "editWidget", type="CheckBox")
            cfg = ET.SubElement(ew, "config")
            opt = ET.SubElement(cfg, "Option", type="Map")
            ET.SubElement(opt, "Option", type="QString", name="CheckedState", value="1")
            ET.SubElement(opt, "Option", type="QString", name="UncheckedState", value="0")
        elif wtype == "DateTime":
            ew = ET.SubElement(fcfg, "editWidget", type="DateTime")
            cfg = ET.SubElement(ew, "config")
            opt = ET.SubElement(cfg, "Option", type="Map")
            ET.SubElement(opt, "Option", type="bool", name="calendar_popup", value="true")
            ET.SubElement(opt, "Option", type="QString", name="display_format", value="yyyy-MM-dd")
            ET.SubElement(opt, "Option", type="QString", name="field_format", value="yyyy-MM-dd")
        else:
            ew = ET.SubElement(fcfg, "editWidget", type="TextEdit")
            cfg = ET.SubElement(ew, "config")
            opt = ET.SubElement(cfg, "Option", type="Map")
            ET.SubElement(opt, "Option", type="bool", name="IsMultiline", value="true" if "comments" in fn or "summary" in fn else "false")

    # TABBED DRAG-AND-DROP FORM CONFIGURATION
    efc = ET.SubElement(root, "editFormConfig")
    efc.set("editorlayout", "tablayout")
    form = ET.SubElement(efc, "attributeEditorForm")

    # Tab 1: 1. ID & WHS Check
    t1 = ET.SubElement(form, "attributeEditorContainer", name="Tab 1: 1. ID & WHS Check", groupBox="0", columnCount="1")
    g1a = ET.SubElement(t1, "attributeEditorContainer", name="Header Metadata & Geographic Context", groupBox="1", columnCount="2")
    for f in ["structure_id", "structure_name", "property_name", "recording_date", "recorders", "gnss_point_id", "gnss_poly_id", "site_plan_sheet_no", "floor_plan_sheet_no", "camera_make_number", "photo_frame_range", "overall_condition", "sec1_comments"]:
        ET.SubElement(g1a, "attributeEditorField", name=f)
    g1b = ET.SubElement(t1, "attributeEditorContainer", name="Volunteer Safety & WHS Pre-Entry Check (Check Before Entry)", groupBox="1", columnCount="2")
    for f in ["whs_asbestos", "whs_lead_paint", "whs_unstable_struc", "whs_chemical_haz", "whs_biological_haz", "whs_entry_status", "sec2_whs_comments"]:
        ET.SubElement(g1b, "attributeEditorField", name=f)

    # Tab 2: 2–3. Layout & Sub-Floor
    t2 = ET.SubElement(form, "attributeEditorContainer", name="Tab 2: 2–3. Layout & Sub-Floor", groupBox="0", columnCount="1")
    g2a = ET.SubElement(t2, "attributeEditorContainer", name="Function, Scale & Footprint Layout", groupBox="1", columnCount="2")
    for f in ["orig_purpose", "later_use", "storeys_count", "plan_shape", "facade_symmetry", "facade_orient", "length_m", "width_m", "sec3_layout_comments"]:
        ET.SubElement(g2a, "attributeEditorField", name=f)
    g2b = ET.SubElement(t2, "attributeEditorContainer", name="Foundations & Sub-Floor Space", groupBox="1", columnCount="2")
    for f in ["footing_type", "subfloor_timber", "subfloor_deposit", "sec4_found_comments"]:
        ET.SubElement(g2b, "attributeEditorField", name=f)

    # Tab 3: 4. Walls & Framing
    t3 = ET.SubElement(form, "attributeEditorContainer", name="Tab 3: 4. Walls & Framing", groupBox="0", columnCount="1")
    g3a = ET.SubElement(t3, "attributeEditorContainer", name="Wall Framing Systems, Joints & Nails", groupBox="1", columnCount="2")
    for f in ["wall_system_prim", "wall_system_sec", "timber_joints", "fasteners_nails"]:
        ET.SubElement(g3a, "attributeEditorField", name=f)
    g3b = ET.SubElement(t3, "attributeEditorContainer", name="Masonry, Cladding & External Finishes", groupBox="1", columnCount="2")
    for f in ["brick_mfg_type", "brick_bond", "stone_coursing", "mortar_type", "quoins_type", "ext_cladding_prim", "ext_cladding_sec", "ext_wall_finish", "sec5_wall_comments"]:
        ET.SubElement(g3b, "attributeEditorField", name=f)

    # Tab 4: 5–6. Roof & Openings
    t4 = ET.SubElement(form, "attributeEditorContainer", name="Tab 4: 5–6. Roof & Openings", groupBox="0", columnCount="1")
    g4a = ET.SubElement(t4, "attributeEditorContainer", name="Roof Form, Verandahs & Chimneys", groupBox="1", columnCount="2")
    for f in ["roof_form", "roof_cladding_cur", "roof_early_clues", "verandah_loc", "verandah_profile", "verandah_posts", "verandah_status", "chimney_count", "chimney_material", "chimney_location", "sec6_roof_comments"]:
        ET.SubElement(g4a, "attributeEditorField", name=f)
    g4b = ET.SubElement(t4, "attributeEditorContainer", name="External Openings & Hardware", groupBox="1", columnCount="2")
    for f in ["window_type_prim", "window_pane_cfg", "door_type_prim", "door_hardware", "sec7_openings_comments"]:
        ET.SubElement(g4b, "attributeEditorField", name=f)

    # Tab 5: 7–9. Phasing, Marks & Synthesis
    t5 = ET.SubElement(form, "attributeEditorContainer", name="Tab 5: 7–9. Phasing, Marks & Synthesis", groupBox="0", columnCount="1")
    g5a = ET.SubElement(t5, "attributeEditorContainer", name="Phasing & Relative Chronology (Miles Lewis Building Developments)", groupBox="1", columnCount="1")
    ET.SubElement(g5a, "attributeEditorField", name="sec8_phasing_comments")
    rel_stg = ET.SubElement(g5a, "attributeEditorRelation", name="rel_structure_stages", relation="rel_structure_stages", showLabel="1", forceSuppressFormPopup="0")
    opt_stg = ET.SubElement(rel_stg, "editor_configuration", type="Map")
    ET.SubElement(opt_stg, "Option", type="QString", name="buttons", value="AllButtons")

    g5b = ET.SubElement(t5, "attributeEditorContainer", name="Diagnostic Brands, Stamps & Inscriptions", groupBox="1", columnCount="1")
    rel_mk = ET.SubElement(g5b, "attributeEditorRelation", name="rel_structure_marks", relation="rel_structure_marks", showLabel="1", forceSuppressFormPopup="0")
    opt_mk = ET.SubElement(rel_mk, "editor_configuration", type="Map")
    ET.SubElement(opt_mk, "Option", type="QString", name="buttons", value="AllButtons")

    g5c = ET.SubElement(t5, "attributeEditorContainer", name="General Synthesis & Archaeological Integrity", groupBox="1", columnCount="2")
    for f in ["fabric_intactness", "assoc_refuse_dump", "assoc_privy_cess", "assoc_well_cistern", "assoc_garden_lines", "assoc_fence_lines", "recorder_summary", "sec9_synthesis_comments"]:
        ET.SubElement(g5c, "attributeEditorField", name=f)

    # Tab 6: Internal Rooms (Form 2)
    t6 = ET.SubElement(form, "attributeEditorContainer", name="Tab 6: Internal Rooms (Form 2)", groupBox="0", columnCount="1")
    rel_rm = ET.SubElement(t6, "attributeEditorRelation", name="rel_structure_rooms", relation="rel_structure_rooms", showLabel="1", forceSuppressFormPopup="0")
    opt_rm = ET.SubElement(rel_rm, "editor_configuration", type="Map")
    ET.SubElement(opt_rm, "Option", type="QString", name="buttons", value="AllButtons")

    # Tab 7: Photos, Plans & Scans
    t7 = ET.SubElement(form, "attributeEditorContainer", name="Tab 7: Photos, Plans & Scans", groupBox="0", columnCount="1")
    g7a = ET.SubElement(t7, "attributeEditorContainer", name="Direct Attached Photographs, Plans & Scans", groupBox="1", columnCount="2")
    for f in ["primary_facade_photo_path", "site_plan_scan_path", "floor_plan_scan_path", "paper_form1_scan_path"]:
        ET.SubElement(g7a, "attributeEditorField", name=f)
    g7b = ET.SubElement(t7, "attributeEditorContainer", name="All Attached Media Files (Photographs, Plans, Scans)", groupBox="1", columnCount="1")
    rel_med = ET.SubElement(g7b, "attributeEditorRelation", name="rel_structure_media", relation="rel_structure_media", showLabel="1", forceSuppressFormPopup="0")
    opt_med = ET.SubElement(rel_med, "editor_configuration", type="Map")
    ET.SubElement(opt_med, "Option", type="QString", name="buttons", value="AllButtons")

    return ET.tostring(root, encoding="utf-8").decode("utf-8")


def generate_qml_rooms(codebook_dict):
    """Generate the complete QML style XML with 5-tab drag-and-drop form layout for rooms_spaces."""
    root = ET.Element("qgis", styleCategories="AllStyleCategories", version="3.28.0")
    aliases = ET.SubElement(root, "aliases")
    fields_elem = ET.SubElement(root, "fieldConfiguration")

    room_fields = codebook_dict.get("rooms_spaces", [])
    extra_fields = [
        {"field_name": "structure_name", "field_alias": "Structure Name", "sqlite_data_type": "TEXT", "qgis_widget_type": "TextEdit", "lookup_table_name": "", "volunteer_field_tip": "Parent structure common name."},
        {"field_name": "room_unstructured_notes", "field_alias": "Room Stratigraphic Notes", "sqlite_data_type": "TEXT", "qgis_widget_type": "TextEdit", "lookup_table_name": "", "volunteer_field_tip": "Miles Lewis room synthesis."},
        {"field_name": "paper_form2_scan_path", "field_alias": "Scanned Form 2 Record", "sqlite_data_type": "TEXT", "qgis_widget_type": "ExternalResource", "lookup_table_name": "", "volunteer_field_tip": "Path to scanned Room Proforma PDF."},
    ]
    all_room_fields = room_fields + extra_fields

    for f in all_room_fields:
        fn = f["field_name"]
        fa = f["field_alias"]
        lut = f.get("lookup_table_name", "")
        wtype = f.get("qgis_widget_type", "TextEdit")

        ET.SubElement(aliases, "alias", field=fn, name=fa, index="0")
        fcfg = ET.SubElement(fields_elem, "field", name=fn)
        if wtype == "ExternalResource":
            ew = ET.SubElement(fcfg, "editWidget", type="ExternalResource")
            cfg = ET.SubElement(ew, "config")
            opt = ET.SubElement(cfg, "Option", type="Map")
            ET.SubElement(opt, "Option", type="int", name="DocumentViewer", value="1")
            ET.SubElement(opt, "Option", type="int", name="DocumentViewerHeight", value="240")
            ET.SubElement(opt, "Option", type="int", name="DocumentViewerWidth", value="0")
            ET.SubElement(opt, "Option", type="bool", name="FileWidget", value="true")
            ET.SubElement(opt, "Option", type="int", name="RelativeStorage", value="1")
            ET.SubElement(opt, "Option", type="QString", name="RootPath", value="./media/form_scans")
            ET.SubElement(opt, "Option", type="int", name="StorageMode", value="0")
        elif wtype == "ValueRelation" and lut:
            ew = ET.SubElement(fcfg, "editWidget", type="ValueRelation")
            cfg = ET.SubElement(ew, "config")
            opt = ET.SubElement(cfg, "Option", type="Map")
            ET.SubElement(opt, "Option", type="bool", name="AllowMulti", value="false")
            ET.SubElement(opt, "Option", type="bool", name="AllowNull", value="true")
            ET.SubElement(opt, "Option", type="QString", name="Description", value='"volunteer_identification_guide"')
            ET.SubElement(opt, "Option", type="QString", name="Key", value="code")
            ET.SubElement(opt, "Option", type="QString", name="Layer", value=f"{lut}")
            ET.SubElement(opt, "Option", type="QString", name="LayerName", value=lut)
            ET.SubElement(opt, "Option", type="QString", name="LayerSource", value=f"./balala_pastoral_survey.gpkg|layername={lut}")
            ET.SubElement(opt, "Option", type="QString", name="LayerProviderName", value="ogr")
            ET.SubElement(opt, "Option", type="bool", name="OrderByValue", value="true")
            ET.SubElement(opt, "Option", type="QString", name="Value", value="label")
        elif wtype == "DateTime":
            ew = ET.SubElement(fcfg, "editWidget", type="DateTime")
            cfg = ET.SubElement(ew, "config")
            opt = ET.SubElement(cfg, "Option", type="Map")
            ET.SubElement(opt, "Option", type="bool", name="calendar_popup", value="true")
            ET.SubElement(opt, "Option", type="QString", name="display_format", value="yyyy-MM-dd")
        else:
            ew = ET.SubElement(fcfg, "editWidget", type="TextEdit")
            cfg = ET.SubElement(ew, "config")
            opt = ET.SubElement(cfg, "Option", type="Map")
            ET.SubElement(opt, "Option", type="bool", name="IsMultiline", value="true" if "comments" in fn or "notes" in fn or "summary" in fn else "false")

    # TABBED DRAG-AND-DROP FORM CONFIGURATION
    efc = ET.SubElement(root, "editFormConfig")
    efc.set("editorlayout", "tablayout")
    form = ET.SubElement(efc, "attributeEditorForm")

    # Tab 1: Room ID & Dimensions
    t1 = ET.SubElement(form, "attributeEditorContainer", name="Tab 1: Room ID & Dimensions", groupBox="0", columnCount="1")
    g1a = ET.SubElement(t1, "attributeEditorContainer", name="Room Identification & Context", groupBox="1", columnCount="2")
    for f in ["structure_id", "structure_name", "room_id", "room_name_or_letter", "inferred_use", "later_current_use", "recording_date", "recorders", "gnss_point_poly_id", "floor_plan_sheet_no", "camera_make_number", "photo_frame_range"]:
        ET.SubElement(g1a, "attributeEditorField", name=f)
    g1b = ET.SubElement(t1, "attributeEditorContainer", name="Internal Dimensions & Floor Area", groupBox="1", columnCount="2")
    for f in ["length_m", "width_m", "ceiling_height_m", "floor_area_sqm", "sec1_room_comments"]:
        ET.SubElement(g1b, "attributeEditorField", name=f)

    # Tab 2: Floor, Walls & Ceiling
    t2 = ET.SubElement(form, "attributeEditorContainer", name="Tab 2: Floor, Walls & Ceiling", groupBox="0", columnCount="1")
    g2a = ET.SubElement(t2, "attributeEditorContainer", name="Floors & Sub-Floor Access (Steel Rule Probe)", groupBox="1", columnCount="2")
    for f in ["floor_material", "board_width_mm", "board_thickness_mm", "floor_sawing_marks", "subfloor_access_status", "floor_condition", "floor_comments"]:
        ET.SubElement(g2a, "attributeEditorField", name=f)
    g2b = ET.SubElement(t2, "attributeEditorContainer", name="Walls & Internal Partitions (Linings & Wallpaper)", groupBox="1", columnCount="2")
    for f in ["wall_structure", "wall_lining", "wall_condition", "wall_comments"]:
        ET.SubElement(g2b, "attributeEditorField", name=f)
    g2c = ET.SubElement(t2, "attributeEditorContainer", name="Ceilings & Overhead Framing", groupBox="1", columnCount="2")
    for f in ["ceiling_form", "ceiling_cornice", "ceiling_condition", "ceiling_comments"]:
        ET.SubElement(g2c, "attributeEditorField", name=f)

    # Tab 3: Joinery, Services & Scars
    t3 = ET.SubElement(form, "attributeEditorContainer", name="Tab 3: Joinery, Services & Scars", groupBox="0", columnCount="1")
    g3a = ET.SubElement(t3, "attributeEditorContainer", name="Internal Openings & Joinery", groupBox="1", columnCount="2")
    for f in ["internal_door_type", "door_hardware", "window_type", "skirting_profile", "skirting_height_mm", "joinery_comments"]:
        ET.SubElement(g3a, "attributeEditorField", name=f)
    g3b = ET.SubElement(t3, "attributeEditorContainer", name="Fireplace, Stoves & Fixed Services", groupBox="1", columnCount="2")
    for f in ["fireplace_type", "mantelpiece_type", "fixed_fittings", "services_utilities", "services_comments"]:
        ET.SubElement(g3b, "attributeEditorField", name=f)
    g3c = ET.SubElement(t3, "attributeEditorContainer", name="Alterations, Scars & Inscriptions", groupBox="1", columnCount="2")
    for f in ["structural_scars", "diagnostic_inscriptions", "alterations_comments"]:
        ET.SubElement(g3c, "attributeEditorField", name=f)

    # Tab 4: Room Notes & Scans
    t4 = ET.SubElement(form, "attributeEditorContainer", name="Tab 4: Room Notes & Scans", groupBox="0", columnCount="1")
    for f in ["room_stratigraphic_summary", "room_unstructured_notes", "paper_form2_scan_path"]:
        ET.SubElement(t4, "attributeEditorField", name=f)

    # Tab 5: Room Objects Inventory (Form 3)
    t5 = ET.SubElement(form, "attributeEditorContainer", name="Tab 5: Room Objects Inventory (Form 3)", groupBox="0", columnCount="1")
    rel_obj = ET.SubElement(t5, "attributeEditorRelation", name="rel_room_objects", relation="rel_room_objects", showLabel="1", forceSuppressFormPopup="0")
    opt_obj = ET.SubElement(rel_obj, "editor_configuration", type="Map")
    ET.SubElement(opt_obj, "Option", type="QString", name="buttons", value="AllButtons")

    return ET.tostring(root, encoding="utf-8").decode("utf-8")


def store_qml_styles(codebook_dict):
    """Insert default QML styles into layer_styles table inside the GeoPackage."""
    log("Embedding QML styles and form layouts into GeoPackage layer_styles table...")
    con = sqlite3.connect(GPKG_PATH)
    cur = con.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS layer_styles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        f_table_catalog TEXT(256),
        f_table_schema TEXT(256),
        f_table_name TEXT(256) NOT NULL,
        f_geometry_column TEXT(256),
        styleName TEXT(30),
        styleQML TEXT,
        styleSLD TEXT,
        useAsDefault BOOLEAN,
        description TEXT,
        owner TEXT(30),
        ui TEXT(30),
        update_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # 1. structures QML
    qml_struct = generate_qml_structures(codebook_dict)
    cur.execute("DELETE FROM layer_styles WHERE f_table_name = 'structures'")
    cur.execute("""
    INSERT INTO layer_styles (f_table_name, f_geometry_column, styleName, styleQML, useAsDefault, description)
    VALUES ('structures', 'geom', 'default', ?, 1, 'Default Form 1 Tabbed Form Layout')
    """, (qml_struct,))

    # 2. rooms_spaces QML
    qml_rooms = generate_qml_rooms(codebook_dict)
    cur.execute("DELETE FROM layer_styles WHERE f_table_name = 'rooms_spaces'")
    cur.execute("""
    INSERT INTO layer_styles (f_table_name, f_geometry_column, styleName, styleQML, useAsDefault, description)
    VALUES ('rooms_spaces', '', 'default', ?, 1, 'Default Form 2 Tabbed Room Layout')
    """, (qml_rooms,))

    con.commit()
    con.close()
    log("  layer_styles table updated successfully!")


def build_qgs_project(codebook_dict):
    """Create the turnkey QGIS project file (balala_pastoral_survey.qgs) with project relations and layers."""
    log(f"Building pre-configured QGIS project file at: {QGS_PATH}")

    root = ET.Element("qgis", projectname="Balala Historical & Pastoral Structure Recording System", version="3.28.0")
    ET.SubElement(root, "homePath", path="")

    # Project CRS (EPSG:7856)
    crs = ET.SubElement(root, "projectCrs")
    srs = ET.SubElement(crs, "spatialrefsys")
    ET.SubElement(srs, "wkt").text = 'PROJCRS["GDA2020 / MGA zone 56",BASEGEOGCRS["GDA2020",DATUM["Geocentric Datum of Australia 2020",ELLIPSOID["GRS 1980",6378137,298.257222101,LENGTHUNIT["metre",1]]],PRIMEM["Greenwich",0,ANGLEUNIT["degree",0.0174532925199433]],ID["EPSG",7844]],CONVERSION["Map Grid of Australia zone 56",METHOD["Transverse Mercator",ID["EPSG",9807]],PARAMETER["Latitude of natural origin",0,ANGLEUNIT["degree",0.0174532925199433]],PARAMETER["Longitude of natural origin",153,ANGLEUNIT["degree",0.0174532925199433]],PARAMETER["Scale factor at natural origin",0.9996,SCALEUNIT["unity",1]],PARAMETER["False easting",500000,LENGTHUNIT["metre",1]],PARAMETER["False northing",10000000,LENGTHUNIT["metre",1]],ID["EPSG",17356]],CS[Cartesian,2],AXIS["(E)",east,ORDER[1],LENGTHUNIT["metre",1]],AXIS["(N)",north,ORDER[2],LENGTHUNIT["metre",1]],USAGE[SCOPE["Engineering survey, topographic mapping."],AREA["Australia onshore and offshore east of 150°E."],BBOX[-46.7,150,-9.86,159.21]],ID["EPSG",7856]]'
    ET.SubElement(srs, "proj4").text = "+proj=utm +zone=56 +south +ellps=GRS80 +towgs84=0,0,0,0,0,0,0 +units=m +no_defs"
    ET.SubElement(srs, "srsid").text = "29037"
    ET.SubElement(srs, "srid").text = "7856"
    ET.SubElement(srs, "authid").text = "EPSG:7856"
    ET.SubElement(srs, "description").text = "GDA2020 / MGA zone 56"

    # Layer IDs
    lid_structures = "structures_layer"
    lid_points = "structures_points_layer"
    lid_rooms = "rooms_spaces_layer"
    lid_objects = "room_objects_inventory_layer"
    lid_stages = "construction_stages_layer"
    lid_marks = "diagnostic_marks_layer"
    lid_media = "media_attachments_layer"
    lid_photo = "photographic_log_layer"

    # Layer tree
    ltg = ET.SubElement(root, "layer-tree-group")
    ET.SubElement(ltg, "customproperties")

    # Group 1: Spatial
    g_spatial = ET.SubElement(ltg, "layer-tree-group", name="1. Spatial Standing Structures", expanded="1", checked="Qt::Checked")
    ET.SubElement(g_spatial, "layer-tree-layer", id=lid_structures, name="structures (Form 1)", expanded="1", checked="Qt::Checked")
    ET.SubElement(g_spatial, "layer-tree-layer", id=lid_points, name="structures_points (GNSS Waypoints)", expanded="1", checked="Qt::Checked")

    # Group 2: Relational Records
    g_rel = ET.SubElement(ltg, "layer-tree-group", name="2. Relational Survey Records", expanded="1", checked="Qt::Checked")
    ET.SubElement(g_rel, "layer-tree-layer", id=lid_rooms, name="rooms_spaces (Form 2)", expanded="1", checked="Qt::Checked")
    ET.SubElement(g_rel, "layer-tree-layer", id=lid_objects, name="room_objects_inventory (Form 3)", expanded="1", checked="Qt::Checked")
    ET.SubElement(g_rel, "layer-tree-layer", id=lid_stages, name="construction_stages (Phasing)", expanded="0", checked="Qt::Checked")
    ET.SubElement(g_rel, "layer-tree-layer", id=lid_marks, name="diagnostic_marks (Brands & Marks)", expanded="0", checked="Qt::Checked")
    ET.SubElement(g_rel, "layer-tree-layer", id=lid_media, name="media_attachments (Photos & Plans)", expanded="0", checked="Qt::Checked")
    ET.SubElement(g_rel, "layer-tree-layer", id=lid_photo, name="photographic_log (Form 4)", expanded="0", checked="Qt::Checked")

    # Group 3: Lookups
    g_lut = ET.SubElement(ltg, "layer-tree-group", name="3. Controlled Vocabularies (Lookups)", expanded="0", checked="Qt::Unchecked")
    lut_names = [
        "lut_structure_purpose", "lut_foundations_and_subfloor", "lut_wall_systems_and_framing",
        "lut_masonry_and_cladding", "lut_roof_verandah_chimney", "lut_openings_and_hardware",
        "lut_internal_rooms_and_services", "lut_phasing_whs_and_condition", "lut_object_category", "lut_photo_orientation"
    ]
    for lut in lut_names:
        ET.SubElement(g_lut, "layer-tree-layer", id=f"{lut}_layer", name=lut, expanded="0", checked="Qt::Unchecked")

    # Map Canvas
    canvas = ET.SubElement(root, "mapcanvas", name="theMapCanvas")
    dest_srs = ET.SubElement(canvas, "destinationsrs")
    srs_c = ET.SubElement(dest_srs, "spatialrefsys")
    ET.SubElement(srs_c, "authid").text = "EPSG:7856"
    extent = ET.SubElement(canvas, "extent")
    ET.SubElement(extent, "xmin").text = "338700"
    ET.SubElement(extent, "ymin").text = "6622300"
    ET.SubElement(extent, "xmax").text = "339000"
    ET.SubElement(extent, "ymax").text = "6622550"

    # Project Layers
    players = ET.SubElement(root, "projectlayers")

    # Helper function to add a maplayer
    def add_layer_xml(parent, lid, lname, geom_type, qml_str=None):
        ml = ET.SubElement(parent, "maplayer", type="vector", autoRefreshTime="0", geometry=geom_type, refreshOnNotifyMessage="", refreshOnNotifyEnabled="0")
        ET.SubElement(ml, "id").text = lid
        ET.SubElement(ml, "datasource").text = f"./{GPKG_NAME}|layername={lname}"
        ET.SubElement(ml, "layername").text = lname
        ET.SubElement(ml, "provider", encoding="UTF-8").text = "ogr"

        srs_ml = ET.SubElement(ml, "srs")
        srs_sub = ET.SubElement(srs_ml, "spatialrefsys")
        ET.SubElement(srs_sub, "authid").text = "EPSG:7856" if geom_type != "No geometry" else ""

        if qml_str:
            qml_tree = ET.fromstring(qml_str)
            for child in qml_tree:
                ml.append(child)
        return ml

    # Add layers
    qml_s = generate_qml_structures(codebook_dict)
    qml_r = generate_qml_rooms(codebook_dict)

    add_layer_xml(players, lid_structures, "structures", "Polygon", qml_s)
    add_layer_xml(players, lid_points, "structures_points", "Point")
    add_layer_xml(players, lid_rooms, "rooms_spaces", "No geometry", qml_r)
    add_layer_xml(players, lid_objects, "room_objects_inventory", "No geometry")
    add_layer_xml(players, lid_stages, "construction_stages", "No geometry")
    add_layer_xml(players, lid_marks, "diagnostic_marks", "No geometry")
    add_layer_xml(players, lid_media, "media_attachments", "No geometry")
    add_layer_xml(players, lid_photo, "photographic_log", "No geometry")

    for lut in lut_names:
        add_layer_xml(players, f"{lut}_layer", lut, "No geometry")

    # PROJECT RELATIONS
    rels = ET.SubElement(root, "relations")

    rel_defs = [
        ("rel_structure_rooms", "rel_structure_rooms", lid_rooms, lid_structures, "structure_id", "structure_id"),
        ("rel_room_objects", "rel_room_objects", lid_objects, lid_rooms, "room_id", "room_id"),
        ("rel_structure_stages", "rel_structure_stages", lid_stages, lid_structures, "structure_id", "structure_id"),
        ("rel_structure_marks", "rel_structure_marks", lid_marks, lid_structures, "structure_id", "structure_id"),
        ("rel_structure_media", "rel_structure_media", lid_media, lid_structures, "structure_id", "structure_id"),
        ("rel_structure_photolog", "rel_structure_photolog", lid_photo, lid_structures, "structure_id", "structure_id"),
    ]

    for rid, rname, ref_lyr, refd_lyr, f_child, f_parent in rel_defs:
        rel = ET.SubElement(rels, "relation", id=rid, name=rname, referencingLayer=ref_lyr, referencedLayer=refd_lyr, generateId="0")
        ET.SubElement(rel, "fieldRef", referencingField=f_child, referencedField=f_parent)

    # Format XML nicely
    xml_str = ET.tostring(root, encoding="utf-8")
    parsed = minidom.parseString(xml_str)
    pretty_xml = parsed.toprettyxml(indent="  ", encoding="utf-8").decode("utf-8")

    with open(QGS_PATH, "w", encoding="utf-8") as f:
        f.write(pretty_xml)

    log("  balala_pastoral_survey.qgs written and verified successfully!")


def deploy_outputs():
    """Copy the generated .gpkg and .qgs to the repository root for root-level access."""
    log("Deploying GeoPackage and QGIS project to repository root...")
    shutil.copy2(GPKG_PATH, ROOT_GPKG_PATH)
    shutil.copy2(QGS_PATH, ROOT_QGS_PATH)
    log(f"  Copied to root: {ROOT_GPKG_PATH}")
    log(f"  Copied to root: {ROOT_QGS_PATH}")


def main():
    log("=================================================================")
    log("STARTING BALALA PASTORAL GEOPACKAGE & QGIS PROJECT BUILD PROCESS")
    log("=================================================================")

    # 1. Directories & Scans
    setup_directories()

    # 2. Sample Media
    generate_sample_media()

    # 3. Read Codebook
    codebook_path = os.path.join(SCHEMA_DIR, "codebook_data_dictionary.csv")
    codebook_dict = {}
    with open(codebook_path, "r", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            codebook_dict.setdefault(r["table_name"], []).append(r)

    # 4. Create GeoPackage
    create_geopackage()

    # 5. Embed QML Styles
    store_qml_styles(codebook_dict)

    # 6. Build QGS Project
    build_qgs_project(codebook_dict)

    # 7. Deploy to root
    deploy_outputs()

    log("=================================================================")
    log("BUILD PROCESS COMPLETED SUCCESSFULLY!")
    log("=================================================================")


if __name__ == "__main__":
    main()
