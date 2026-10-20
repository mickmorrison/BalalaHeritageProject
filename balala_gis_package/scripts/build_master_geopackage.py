#!/usr/bin/env python3
"""
Balala Heritage Project - Master Spatial Database Build Script
==============================================================
Instantiates the master GeoPackage (`balala_master.gpkg`) aligning 1:1 with
the Balala field data recording forms:
  - Form 1: Z+F IMAGER 5016 Scan Station Register & Integrity Sheet (`tls_stations`, `tls_targets`)
  - Form 2: RTK GNSS Field Log & Heritage Feature Point Register (`rtk_survey_points`, `heritage_features`, `rtk_base_sessions`, `rtk_calibration_checks`)

Datum: GDA2020 / MGA Zone 56 (EPSG:7856)
Vertical: AHD via AUSGeoid2020
"""

import os
import sys
import csv
import sqlite3
from osgeo import gdal, ogr, osr

gdal.UseExceptions()

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PKG_DIR = os.path.dirname(SCRIPT_DIR)
REPO_ROOT = os.path.dirname(PKG_DIR)
SCHEMA_DIR = os.path.join(REPO_ROOT, "schema")

GPKG_PATH = os.path.join(REPO_ROOT, "balala_master.gpkg")
PKG_GPKG_PATH = os.path.join(PKG_DIR, "balala_master.gpkg")

def log(msg):
    print(f"[BUILD-MASTER-GPKG] {msg}")

def build_master_gpkg():
    log(f"Building master GeoPackage: {GPKG_PATH}...")
    if os.path.exists(GPKG_PATH):
        try:
            os.remove(GPKG_PATH)
        except Exception:
            pass

    driver = ogr.GetDriverByName("GPKG")
    ds = driver.CreateDataSource(GPKG_PATH)
    if not ds:
        raise RuntimeError(f"Could not create GeoPackage at {GPKG_PATH}")

    # Spatial Reference System: GDA2020 / MGA Zone 56 (EPSG:7856)
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(7856)
    srs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)

    # ---------------------------------------------------------
    # 1. SPATIAL LAYER: rtk_survey_points (Point)
    # ---------------------------------------------------------
    log("Creating spatial layer: rtk_survey_points (Point, EPSG:7856)...")
    lyr_rtk = ds.CreateLayer("rtk_survey_points", srs, ogr.wkbPoint25D)
    
    rtk_fields = [
        ("point_id", ogr.OFTString, 50),
        ("time", ogr.OFTString, 10),
        ("feat_code", ogr.OFTString, 50),
        ("pole_ht_m", ogr.OFTReal, 0),
        ("status", ogr.OFTString, 20),
        ("pdop", ogr.OFTReal, 0),
        ("h_rms_mm", ogr.OFTReal, 0),
        ("v_rms_mm", ogr.OFTReal, 0),
        ("photo_id", ogr.OFTString, 100),
        ("field_notes_attributes", ogr.OFTString, 500),
        ("heritage_feature_id", ogr.OFTString, 50),
        ("easting_m", ogr.OFTReal, 0),
        ("northing_m", ogr.OFTReal, 0),
        ("height_ahd_m", ogr.OFTReal, 0),
        ("session_id", ogr.OFTString, 50),
    ]
    for fn, ft, w in rtk_fields:
        fld = ogr.FieldDefn(fn, ft)
        if w > 0:
            fld.SetWidth(w)
        lyr_rtk.CreateField(fld)

    # ---------------------------------------------------------
    # 2. SPATIAL LAYER: tls_stations (Point)
    # ---------------------------------------------------------
    log("Creating spatial layer: tls_stations (Point, EPSG:7856)...")
    lyr_tls = ds.CreateLayer("tls_stations", srs, ogr.wkbPoint25D)
    
    tls_fields = [
        ("station_id", ogr.OFTString, 50),
        ("project_id", ogr.OFTString, 100),
        ("survey_date", ogr.OFTDate, 0),
        ("operator", ogr.OFTString, 100),
        ("weather_desc", ogr.OFTString, 255),
        ("temp_celsius", ogr.OFTReal, 0),
        ("pressure_hpa", ogr.OFTReal, 0),
        ("humidity_pct", ogr.OFTReal, 0),
        ("instrument_model", ogr.OFTString, 50),
        ("serial_no", ogr.OFTString, 50),
        ("firmware_ver", ogr.OFTString, 50),
        ("raw_file_prefix", ogr.OFTString, 50),
        ("time_start", ogr.OFTString, 10),
        ("hi_m", ogr.OFTReal, 0),
        ("res_setting", ogr.OFTString, 50),
        ("quality_mode", ogr.OFTString, 20),
        ("hdr_color", ogr.OFTInteger, 0),
        ("occupied_mark_id", ogr.OFTString, 50),
        ("control_target_ids", ogr.OFTString, 255),
        ("raw_filename", ogr.OFTString, 100),
        ("sha256_verified", ogr.OFTInteger, 0),
        ("target_feature", ogr.OFTString, 255),
        ("easting_m", ogr.OFTReal, 0),
        ("northing_m", ogr.OFTReal, 0),
        ("height_ahd_m", ogr.OFTReal, 0),
    ]
    for fn, ft, w in tls_fields:
        fld = ogr.FieldDefn(fn, ft)
        if w > 0:
            fld.SetWidth(w)
        lyr_tls.CreateField(fld)

    # ---------------------------------------------------------
    # 3. SPATIAL LAYER: heritage_features (Point / Polygon)
    # ---------------------------------------------------------
    log("Creating spatial layer: heritage_features (MultiPolygon, EPSG:7856)...")
    lyr_heritage = ds.CreateLayer("heritage_features", srs, ogr.wkbMultiPolygon)
    
    heritage_fields = [
        ("feature_id", ogr.OFTString, 50),
        ("feat_code", ogr.OFTString, 50),
        ("feature_name", ogr.OFTString, 150),
        ("structure_id", ogr.OFTString, 50),
        ("description", ogr.OFTString, 500),
        ("cultural_tradition", ogr.OFTString, 50),
        ("period_epoch", ogr.OFTString, 50),
        ("preservation_state", ogr.OFTString, 50),
    ]
    for fn, ft, w in heritage_fields:
        fld = ogr.FieldDefn(fn, ft)
        if w > 0:
            fld.SetWidth(w)
        lyr_heritage.CreateField(fld)

    # ---------------------------------------------------------
    # 4. ATTRIBUTE TABLE: tls_targets
    # ---------------------------------------------------------
    log("Creating attribute table: tls_targets...")
    tbl_targets = ds.CreateLayer("tls_targets", None, ogr.wkbNone)
    for fn, ft, w in [
        ("target_id", ogr.OFTString, 50),
        ("station_id", ogr.OFTString, 50),
        ("target_type", ogr.OFTString, 50),
        ("rtk_tie_id", ogr.OFTString, 50),
        ("est_distance_m", ogr.OFTReal, 0),
        ("mounting_ht_m", ogr.OFTReal, 0),
        ("station_sightings_notes", ogr.OFTString, 255),
    ]:
        fld = ogr.FieldDefn(fn, ft)
        if w > 0:
            fld.SetWidth(w)
        tbl_targets.CreateField(fld)

    # ---------------------------------------------------------
    # 5. ATTRIBUTE TABLE: rtk_base_sessions
    # ---------------------------------------------------------
    log("Creating attribute table: rtk_base_sessions...")
    tbl_sessions = ds.CreateLayer("rtk_base_sessions", None, ogr.wkbNone)
    for fn, ft, w in [
        ("session_id", ogr.OFTString, 50),
        ("job_id", ogr.OFTString, 50),
        ("date", ogr.OFTDate, 0),
        ("operator", ogr.OFTString, 100),
        ("crs_horiz", ogr.OFTString, 100),
        ("crs_vert", ogr.OFTString, 100),
        ("base_mode", ogr.OFTString, 50),
        ("base_model", ogr.OFTString, 50),
        ("base_sn", ogr.OFTString, 50),
        ("base_point_id", ogr.OFTString, 50),
        ("base_hi_m", ogr.OFTReal, 0),
        ("meas_type", ogr.OFTString, 20),
        ("rover_model", ogr.OFTString, 50),
        ("rover_sn", ogr.OFTString, 50),
        ("controller_id", ogr.OFTString, 50),
        ("pole_height_m", ogr.OFTReal, 0),
        ("raw_controller_file", ogr.OFTString, 100),
        ("exported_file", ogr.OFTString, 100),
        ("gpkg_ingest_date", ogr.OFTDate, 0),
        ("operator_signature", ogr.OFTString, 100),
    ]:
        fld = ogr.FieldDefn(fn, ft)
        if w > 0:
            fld.SetWidth(w)
        tbl_sessions.CreateField(fld)

    # ---------------------------------------------------------
    # 6. ATTRIBUTE TABLE: rtk_calibration_checks
    # ---------------------------------------------------------
    log("Creating attribute table: rtk_calibration_checks...")
    tbl_qc = ds.CreateLayer("rtk_calibration_checks", None, ogr.wkbNone)
    for fn, ft, w in [
        ("check_id", ogr.OFTString, 50),
        ("session_id", ogr.OFTString, 50),
        ("check_type", ogr.OFTString, 50),
        ("time", ogr.OFTString, 10),
        ("bm_id", ogr.OFTString, 50),
        ("known_e", ogr.OFTReal, 0),
        ("known_n", ogr.OFTReal, 0),
        ("known_rl", ogr.OFTReal, 0),
        ("obs_e", ogr.OFTReal, 0),
        ("obs_n", ogr.OFTReal, 0),
        ("obs_rl", ogr.OFTReal, 0),
        ("delta_e_mm", ogr.OFTReal, 0),
        ("delta_n_mm", ogr.OFTReal, 0),
        ("delta_z_mm", ogr.OFTReal, 0),
        ("qc_pass", ogr.OFTInteger, 0),
    ]:
        fld = ogr.FieldDefn(fn, ft)
        if w > 0:
            fld.SetWidth(w)
        tbl_qc.CreateField(fld)

    # ---------------------------------------------------------
    # 7. LOOKUP TABLE: lut_rtk_feat_code
    # ---------------------------------------------------------
    log("Creating lookup table: lut_rtk_feat_code...")
    tbl_lut_code = ds.CreateLayer("lut_rtk_feat_code", None, ogr.wkbNone)
    for fn, ft, w in [
        ("code", ogr.OFTString, 50),
        ("category", ogr.OFTString, 50),
        ("label", ogr.OFTString, 100),
        ("qfield_symbology_hint", ogr.OFTString, 100),
        ("description", ogr.OFTString, 255),
    ]:
        fld = ogr.FieldDefn(fn, ft)
        if w > 0:
            fld.SetWidth(w)
        tbl_lut_code.CreateField(fld)

    # Ingest CSV rows into lut_rtk_feat_code
    lut_csv = os.path.join(SCHEMA_DIR, "lut_rtk_feat_code.csv")
    if os.path.exists(lut_csv):
        with open(lut_csv, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for r in reader:
                feat = ogr.Feature(tbl_lut_code.GetLayerDefn())
                feat.SetField("code", r.get("code", ""))
                feat.SetField("category", r.get("category", ""))
                feat.SetField("label", r.get("label", ""))
                feat.SetField("qfield_symbology_hint", r.get("qfield_symbology_hint", ""))
                feat.SetField("description", r.get("description", ""))
                tbl_lut_code.CreateFeature(feat)

    # ---------------------------------------------------------
    # Insert Sample Field Data for Immediate Verification
    # ---------------------------------------------------------
    log("Inserting representative field survey calibration data (Balala Woolshed)...")
    
    # Base Session
    feat_sess = ogr.Feature(tbl_sessions.GetLayerDefn())
    feat_sess.SetField("session_id", "SESS_20261020_01")
    feat_sess.SetField("job_id", "BAL_RTK_20261020")
    feat_sess.SetField("date", "2026-10-20")
    feat_sess.SetField("operator", "M. Morrison & Survey Crew")
    feat_sess.SetField("crs_horiz", "GDA2020 / MGA Zone 56 (EPSG:7856)")
    feat_sess.SetField("crs_vert", "AHD (AUSGeoid2020)")
    feat_sess.SetField("base_mode", "Base on Known Station")
    feat_sess.SetField("base_model", "Topcon HiPer VR")
    feat_sess.SetField("base_sn", "1142-VR01")
    feat_sess.SetField("base_point_id", "BAL_BM01")
    feat_sess.SetField("base_hi_m", 1.845)
    feat_sess.SetField("meas_type", "Vertical")
    feat_sess.SetField("rover_model", "Topcon HiPer VR")
    feat_sess.SetField("rover_sn", "1142-VR02")
    feat_sess.SetField("controller_id", "FC-6000 #01")
    feat_sess.SetField("pole_height_m", 2.000)
    feat_sess.SetField("raw_controller_file", "BAL_20261020.job")
    feat_sess.SetField("exported_file", "BAL_RTK_PTS_20261020.csv")
    feat_sess.SetField("gpkg_ingest_date", "2026-10-20")
    feat_sess.SetField("operator_signature", "M. Morrison")
    tbl_sessions.CreateFeature(feat_sess)

    # QC Calibration Checks
    for check_type, t, de, dn, dz in [
        ("Start-of-Day Check", "07:45", 4.0, -3.0, 6.0),
        ("End-of-Day Closure", "17:15", -5.0, 2.0, -8.0)
    ]:
        qc = ogr.Feature(tbl_qc.GetLayerDefn())
        qc.SetField("check_id", f"QC_{t.replace(':', '')}")
        qc.SetField("session_id", "SESS_20261020_01")
        qc.SetField("check_type", check_type)
        qc.SetField("time", t)
        qc.SetField("bm_id", "BAL_BM01")
        qc.SetField("known_e", 325410.250)
        qc.SetField("known_n", 6621450.800)
        qc.SetField("known_rl", 945.120)
        qc.SetField("obs_e", 325410.250 + de/1000.0)
        qc.SetField("obs_n", 6621450.800 + dn/1000.0)
        qc.SetField("obs_rl", 945.120 + dz/1000.0)
        qc.SetField("delta_e_mm", de)
        qc.SetField("delta_n_mm", dn)
        qc.SetField("delta_z_mm", dz)
        qc.SetField("qc_pass", 1)
        tbl_qc.CreateFeature(qc)

    # Sample RTK Points (BM, TLS Target Sphere, Heritage Building Corner, Knapped Glass)
    sample_pts = [
        ("1001", "08:10", "BM_PEG", 2.000, "Fixed", 1.4, 6.2, 9.8, "IMG_0101", "Permanent control peg at Woolshed yard gate", 325410.254, 6621450.797, 945.126),
        ("1002", "08:25", "TLS_SPH", 1.850, "Fixed", 1.3, 5.1, 8.4, "IMG_0102", "Target sphere TRG_SPH01 on heavy magnetic mount", 325418.620, 6621462.150, 946.350),
        ("1003", "08:32", "TLS_CHK", 1.500, "Fixed", 1.3, 5.8, 9.1, "IMG_0103", "B&W checkerboard TRG_CHK01 on eastern wall stud", 325425.440, 6621470.210, 947.110),
        ("1004", "08:45", "HIST_BLD", 2.000, "Fixed", 1.5, 7.2, 11.0, "IMG_0104", "STR-01 Main Woolshed NE corner timber stump", 325430.120, 6621480.550, 945.880),
        ("1005", "09:05", "ART_KNPGLS", 2.000, "Fixed", 1.2, 4.8, 7.9, "IMG_0105", "Flaked green bottle glass scraper (post-contact)", 325442.800, 6621495.300, 945.420),
    ]
    for pid, tm, cd, pl, st, pd, hr, vr, ph, nts, e, n, z in sample_pts:
        p_feat = ogr.Feature(lyr_rtk.GetLayerDefn())
        p_feat.SetField("point_id", pid)
        p_feat.SetField("time", tm)
        p_feat.SetField("feat_code", cd)
        p_feat.SetField("pole_ht_m", pl)
        p_feat.SetField("status", st)
        p_feat.SetField("pdop", pd)
        p_feat.SetField("h_rms_mm", hr)
        p_feat.SetField("v_rms_mm", vr)
        p_feat.SetField("photo_id", ph)
        p_feat.SetField("field_notes_attributes", nts)
        p_feat.SetField("easting_m", e)
        p_feat.SetField("northing_m", n)
        p_feat.SetField("height_ahd_m", z)
        p_feat.SetField("session_id", "SESS_20261020_01")
        
        geom = ogr.Geometry(ogr.wkbPoint25D)
        geom.AddPoint(e, n, z)
        p_feat.SetGeometry(geom)
        lyr_rtk.CreateFeature(p_feat)

    # Sample TLS Stations (Z+F 5016)
    sample_stations = [
        ("BAL_ST001", "2026-10-20", "08:20", 1.542, "Normal", "2x", 1, "1001", "TRG_SPH01, TRG_CHK01", "BAL_ST001.zfs", 1, "Woolshed East Apron / Yard Entrance", 325410.254, 6621450.797, 946.668),
        ("BAL_ST002", "2026-10-20", "08:55", 1.510, "High", "4x", 1, "", "TRG_SPH01, TRG_SPH02, TRG_CHK01", "BAL_ST002.zfs", 1, "Woolshed Shearing Board Central Bay", 325422.100, 6621468.300, 946.630),
    ]
    for st_id, s_dt, tm, hi, res, qm, hdr, mark, trgs, raw, fixity, desc, e, n, z in sample_stations:
        st_feat = ogr.Feature(lyr_tls.GetLayerDefn())
        st_feat.SetField("station_id", st_id)
        st_feat.SetField("project_id", "Balala Heritage Project")
        st_feat.SetField("survey_date", s_dt)
        st_feat.SetField("operator", "M. Morrison & TLS Crew")
        st_feat.SetField("weather_desc", "Clear, 18°C, calm, excellent visibility")
        st_feat.SetField("temp_celsius", 18.2)
        st_feat.SetField("pressure_hpa", 1014.5)
        st_feat.SetField("humidity_pct", 42.0)
        st_feat.SetField("instrument_model", "Z+F IMAGER 5016")
        st_feat.SetField("serial_no", "5016-1048")
        st_feat.SetField("firmware_ver", "v3.2.1")
        st_feat.SetField("raw_file_prefix", "BAL26_")
        st_feat.SetField("time_start", tm)
        st_feat.SetField("hi_m", hi)
        st_feat.SetField("res_setting", res)
        st_feat.SetField("quality_mode", qm)
        st_feat.SetField("hdr_color", hdr)
        st_feat.SetField("occupied_mark_id", mark)
        st_feat.SetField("control_target_ids", trgs)
        st_feat.SetField("raw_filename", raw)
        st_feat.SetField("sha256_verified", fixity)
        st_feat.SetField("target_feature", desc)
        st_feat.SetField("easting_m", e)
        st_feat.SetField("northing_m", n)
        st_feat.SetField("height_ahd_m", z)

        geom = ogr.Geometry(ogr.wkbPoint25D)
        geom.AddPoint(e, n, z)
        st_feat.SetGeometry(geom)
        lyr_tls.CreateFeature(st_feat)

    # Sample Target Register
    sample_targets = [
        ("TRG_SPH01", "BAL_ST001", "139mm Sphere", "1002", 8.4, 1.85, "Visible from ST001 and ST002; magnetic mount on steel post"),
        ("TRG_CHK01", "BAL_ST001", "B&W Tile", "1003", 14.2, 1.50, "Visible from ST001, ST002; affixed to eastern timber stud"),
        ("TRG_SPH02", "BAL_ST002", "139mm Sphere", "", 6.5, 1.60, "Internal shearing board tie between bays 3 and 4"),
    ]
    for tid, stid, ttype, rtk, dist, mht, nts in sample_targets:
        trg_feat = ogr.Feature(tbl_targets.GetLayerDefn())
        trg_feat.SetField("target_id", tid)
        trg_feat.SetField("station_id", stid)
        trg_feat.SetField("target_type", ttype)
        trg_feat.SetField("rtk_tie_id", rtk)
        trg_feat.SetField("est_distance_m", dist)
        trg_feat.SetField("mounting_ht_m", mht)
        trg_feat.SetField("station_sightings_notes", nts)
        tbl_targets.CreateFeature(trg_feat)

    # Close data source to write and index
    del ds
    log(f"Master GeoPackage successfully instantiated at: {GPKG_PATH}")

    # Copy to balala_gis_package if directory exists
    if os.path.exists(PKG_DIR):
        import shutil
        shutil.copy2(GPKG_PATH, PKG_GPKG_PATH)
        log(f"Companion master GeoPackage updated at: {PKG_GPKG_PATH}")

if __name__ == "__main__":
    build_master_gpkg()
