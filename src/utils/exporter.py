"""
Flent Lens 2.0 — Export Engine
Deliverables:
  1. {City}_Investment_Atlas.kml  — Hex-grid Google Earth map (rich popups)
  2. {City}_Master_Report.xlsx    — 7-sheet Excel workbook
  3. {City}_hex_analysis.geojson  — For Streamlit dashboard
  4. city_summary.json            — Machine-readable KPIs for cross-city analysis
"""
import os, json
import pandas as pd
import geopandas as gpd
import numpy as np
import xml.etree.ElementTree as ET
from datetime import datetime
import config
from src.utils.logger import print_success, print_warning, print_detail, log_process

# ═══════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════
KNS = "http://www.opengis.net/kml/2.2"
def _e(tag): return f'{{{KNS}}}{tag}'
def _fmt(v):
    try: return f"₹{v:,.0f}"
    except: return str(v)
def Fk(x): return f"₹{x/1000:.0f}k" if x > 0 else "N/A"

def _kml_doc(title):
    ET.register_namespace('', KNS)
    kml = ET.Element(_e('kml'))
    doc = ET.SubElement(kml, _e('Document'))
    ET.SubElement(doc, _e('name')).text = title
    return kml, doc

def _add_style(doc, sid, line_color, poly_color, width='1.5'):
    s = ET.SubElement(doc, _e('Style'), id=sid)
    ls = ET.SubElement(s, _e('LineStyle'))
    ET.SubElement(ls, _e('color')).text = line_color
    ET.SubElement(ls, _e('width')).text = width
    ps = ET.SubElement(s, _e('PolyStyle'))
    ET.SubElement(ps, _e('color')).text = poly_color

def _add_icon_style(doc, sid, href, scale='0.8'):
    s = ET.SubElement(doc, _e('Style'), id=sid)
    ics = ET.SubElement(s, _e('IconStyle'))
    ET.SubElement(ics, _e('scale')).text = scale
    icon = ET.SubElement(ics, _e('Icon'))
    ET.SubElement(icon, _e('href')).text = href

def _add_polygon(parent, polygon):
    pe = ET.SubElement(parent, _e('Polygon'))
    ob = ET.SubElement(pe, _e('outerBoundaryIs'))
    lr = ET.SubElement(ob, _e('LinearRing'))
    ET.SubElement(lr, _e('coordinates')).text = " ".join(
        f"{c[0]},{c[1]},0" for c in polygon.exterior.coords)

def _save_kml(kml, path):
    os.makedirs(os.path.dirname(path) if os.path.dirname(path) else '.', exist_ok=True)
    ET.ElementTree(kml).write(path, xml_declaration=True, encoding='utf-8')

def _np(v):
    if isinstance(v, np.integer): return int(v)
    if isinstance(v, np.floating): return float(v)
    if isinstance(v, np.bool_): return bool(v)
    return v

def _g(r, k, d=0):
    v = r.get(k, d)
    return float(v) if pd.notna(v) else d

def _gi(r, k):
    return int(_g(r, k, 0))


# ═══════════════════════════════════════════════════════════════════
# HEX POPUP HTML — Rich data card for KML & dashboard
# ═══════════════════════════════════════════════════════════════════
def _hex_popup(r, tier_colors):
    name = str(r.get('hex_name', r.get('hex_id', '?')[:10]))
    tier = r.get('tier', 'Excluded')
    tc = tier_colors.get(tier, '#94a3b8')
    score = _g(r, 'OPP_SCORE')
    neff = _g(r, 'Neff')
    stability = _g(r, 'stability_score', 1.0)
    margin_apt = _g(r, 'arb_margin_apartment')
    margin_villa = _g(r, 'arb_margin_villa')
    margin_best = _g(r, 'arb_margin_best')
    best_asset = r.get('best_asset_type', 'apartment')
    ddf = _g(r, 'demand_discount', 0.80)
    rent_1bhk = _g(r, 'avg_rent_1bhk')
    ci_low = _g(r, 'rent_1bhk_CI_low')
    ci_high = _g(r, 'rent_1bhk_CI_high')
    pct_nb = _g(r, 'pct_neighbor_sourced') * 100
    sample = _gi(r, 'sample_size')
    demand = _g(r, 'demand_intensity_idx')
    supply_idx = _g(r, 'supply_depth_idx')
    transit = _g(r, 'transit_score')
    employment = _g(r, 'employment_score')
    lifestyle = _g(r, 'lifestyle_score')
    osm_conf = _g(r, 'osm_confidence')
    aura = _g(r, 'aura_multiplier', 1.0)
    aura_src = r.get('aura_sources', 'None')
    if pd.isna(aura_src): aura_src = 'None'
    aura_str = f"+{(aura-1)*100:.1f}%" if aura > 1 else (f"{(aura-1)*100:.1f}%" if aura < 1 else "Neutral")
    
    nearest_transit = r.get('nearest_transit', (None, None))
    nearest_office = r.get('nearest_office', (None, None))
    nearest_lifestyle = r.get('nearest_lifestyle', (None, None))
    n_apt, n_vil = _gi(r, 'n_acq_apt'), _gi(r, 'n_acq_villa')
    cnt3, cnt4 = _gi(r, 'cnt_3bhk'), _gi(r, 'cnt_4bhk')

    # --- Generative AI Executive Summary ---
    def _gen_narrative():
        t_name = nearest_transit[0] if isinstance(nearest_transit, tuple) and nearest_transit[0] else None
        o_name = nearest_office[0] if isinstance(nearest_office, tuple) and nearest_office[0] else None
        
        anchor_txt = f" yields anchor at {_fmt(rent_1bhk)}"
        margin_txt = f"predictable {_fmt(margin_best)} arbitrage margin"
        
        story = f"This micro-market yields a {margin_txt}. With 1BHK {anchor_txt}, subdivisions here mathematically support up to an {ddf*100:.1f}% Elastic DDF."
        
        if t_name and o_name:
            story += f" Premium access to {o_name} and {t_name} heavily insulates tenant demand."
        elif t_name:
            story += f" Proximity to {t_name} serves as a strong tenant magnet."
        
        return story

    html = f"""<div style="width:420px; background:#ffffff; border:1px solid #e2e8f0; box-shadow:0 20px 25px -5px rgba(0,0,0,0.1), 0 8px 10px -6px rgba(0,0,0,0.1); border-radius:12px; overflow:hidden; font-family:'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">"""

    # --- Header (Gradient matched to Tier) ---
    grad_map = {
        'Tier 1': 'linear-gradient(135deg, #14532d 0%, #16a34a 100%)',
        'Tier 2': 'linear-gradient(135deg, #78350f 0%, #d97706 100%)',
        'Tier 3': 'linear-gradient(135deg, #7f1d1d 0%, #dc2626 100%)',
        'Excluded': 'linear-gradient(135deg, #334155 0%, #64748b 100%)'
    }
    header_grad = grad_map.get(tier, grad_map['Excluded'])

    html += f"""
    <div style="background:{header_grad}; padding:18px 20px;">
        <table style="width:100%; border-collapse:collapse;"><tr>
            <td style="vertical-align:middle;">
                <h3 style="margin:0 0 6px 0; font-size:20px; font-weight:800; color:#ffffff; letter-spacing:-0.5px;">{name}</h3>
                <span style="background:rgba(255,255,255,0.2); backdrop-filter:blur(4px); color:#ffffff; padding:4px 8px; border-radius:6px; font-size:11px; font-weight:700; text-transform:uppercase; letter-spacing:0.5px; border:1px solid rgba(255,255,255,0.3);">{tier}</span>
                <span style="background:#0f172a; color:#f8fafc; padding:4px 8px; border-radius:6px; font-size:11px; font-weight:600; margin-left:6px; border:1px solid rgba(255,255,255,0.1);"><span style="color:#fbbf24;">★</span> {best_asset.title()}s</span>
            </td>
            <td style="text-align:right; vertical-align:middle;">
                <div style="background:rgba(255,255,255,0.1); border:1px solid rgba(255,255,255,0.2); border-radius:8px; padding:6px 12px; display:inline-block;">
                    <div style="font-size:26px; font-weight:900; color:#ffffff; line-height:1;">{score:.1f}</div>
                    <div style="font-size:9px; color:#cbd5e1; text-transform:uppercase; font-weight:700; letter-spacing:0.5px; margin-top:2px;">Opp Score</div>
                </div>
            </td>
        </tr></table>
    </div>"""

    # --- Confidence Banner ---
    conf = r.get('confidence', 'unknown')
    if conf == 'full':
        conf_badge, conf_bg, conf_tc = '🟢 High Confidence', '#dcfce7', '#166534'
    elif conf == 'low_confidence':
        conf_badge, conf_bg, conf_tc = '🟡 Low Confidence', '#fef08a', '#854d0e'
    else:
        conf_badge, conf_bg, conf_tc = '🔴 Insufficient Data', '#fee2e2', '#991b1b'

    if conf != 'full':
        html += f"""
    <div style="background:{conf_bg}; padding:8px 20px; border-bottom:1px solid #e2e8f0; display:flex; justify-content:space-between; align-items:center;">
        <div style="font-size:12px; color:{conf_tc}; font-weight:700; letter-spacing:0.3px;">{conf_badge}</div>
        <div style="font-size:11px; color:{conf_tc}; opacity:0.8;">Neff: {neff:.1f} ({pct_nb:.0f}% neighbor avg)</div>
    </div>"""

    # --- AI Executive Summary & Core Metrics ---
    stab_color = '#16a34a' if stability >= 0.85 else ('#d97706' if stability >= 0.70 else '#dc2626')
    
    html += f"""
    <div style="padding:16px 20px 8px 20px;">
        <div style="background:#f0fdf4; border:1px solid #bbf7d0; border-radius:8px; padding:12px; margin-bottom:16px;">
            <div style="font-size:12px; font-weight:700; color:#166534; margin-bottom:4px;">📊 AI Executive Summary</div>
            <div style="font-size:11px; color:#15803d; line-height:1.5;">{_gen_narrative()}</div>
        </div>
        
        <div style="display:grid; grid-template-columns:1fr 1fr; gap:12px;">
            <div style="background:#f8fafc; border:1px solid #e2e8f0; border-radius:8px; padding:10px;">
                <div style="font-size:10px; color:#64748b; font-weight:600; text-transform:uppercase; letter-spacing:0.5px; margin-bottom:2px;">Arbitrage Margin</div>
                <div style="font-size:20px; font-weight:800; color:#0f172a;">{_fmt(margin_best)} <span style="font-size:12px; font-weight:500; color:#64748b;">/mo</span></div>
            </div>
            <div style="background:#f8fafc; border:1px solid #e2e8f0; border-radius:8px; padding:10px;">
                <div style="font-size:10px; color:#64748b; font-weight:600; text-transform:uppercase; letter-spacing:0.5px; margin-bottom:2px;">1BHK Yield Anchor</div>
                <div style="font-size:20px; font-weight:800; color:#0f172a;">{_fmt(rent_1bhk)} <span style="font-size:12px; font-weight:500; color:#64748b;">/mo</span></div>
                <div style="font-size:9px; color:#94a3b8; font-weight:500; margin-top:2px;">CI: {Fk(ci_low)}–{Fk(ci_high)}</div>
            </div>
        </div>
        
        <div style="display:grid; grid-template-columns:1fr 1fr; gap:12px; margin-top:12px; margin-bottom:16px;">
            <div>
                <div style="font-size:10px; color:#64748b; font-weight:600; text-transform:uppercase; letter-spacing:0.5px;">Elastic DDF</div>
                <div style="font-size:15px; font-weight:700; color:#3b82f6;">{ddf*100:.1f}%</div>
            </div>
            <div>
                <div style="font-size:10px; color:#64748b; font-weight:600; text-transform:uppercase; letter-spacing:0.5px;">MAUP Stability</div>
                <div style="font-size:15px; font-weight:700; color:{stab_color};">{stability:.2f} <span style="font-size:10px; font-weight:500; opacity:0.7;">(Res 6-8)</span></div>
            </div>
        </div>
    """

    # --- Hyper-Local Anchor Points ---
    def _tr(cat, tpl):
        if not isinstance(tpl, tuple) or not tpl[0]: return ""
        name, dist = str(tpl[0]), tpl[1]
        name = name[:28] + '...' if len(name)>30 else name
        return f"""
        <tr style="font-size:11px;">
            <td style="padding:6px 0;">{cat}</td>
            <td style="font-weight:600; color:#0f172a;">{name}</td>
            <td style="text-align:right; color:#94a3b8;">{dist} km</td>
        </tr>"""

    h_tr = _tr('Transit 🚇', nearest_transit)
    h_of = _tr('Workplace 🏢', nearest_office)
    h_lf = _tr('Lifestyle ☕', nearest_lifestyle)

    if h_tr or h_of or h_lf:
        html += f"""
        <div style="font-size:10px; font-weight:800; color:#64748b; text-transform:uppercase; letter-spacing:1px; margin-bottom:6px;">Hyper-Local Anchor Points</div>
        <table style="width:100%; text-align:left; border-collapse:collapse; margin-bottom:16px; border-bottom:1px solid #e2e8f0;">
            <tr style="border-bottom:1px solid #e2e8f0; font-size:10px; color:#64748b; text-transform:uppercase;">
                <th style="padding:4px 0;">Category</th>
                <th style="padding:4px 0;">Identity</th>
                <th style="padding:4px 0; text-align:right;">Dist.</th>
            </tr>
            {h_tr}{h_of}{h_lf}
        </table>
        """

    # --- Dual-Track Battle ---
    apt_bg = '#dcfce7' if best_asset == 'apartment' else 'transparent'
    vil_bg = '#dcfce7' if best_asset == 'villa' else 'transparent'
    apt_brd = '#22c55e' if best_asset == 'apartment' else '#e2e8f0'
    vil_brd = '#22c55e' if best_asset == 'villa' else '#e2e8f0'

    html += f"""
        <div style="font-size:10px; font-weight:800; color:#64748b; text-transform:uppercase; letter-spacing:1px; margin-bottom:8px;">Dual-Track Evaluation</div>
        <table style="width:100%; border-collapse:separate; border-spacing:0 4px; margin-bottom:16px;">
            <tr>
                <td style="width:50%; padding:0 4px 0 0;">
                    <div style="background:{apt_bg}; border:1px solid {apt_brd}; border-radius:6px; padding:8px;">
                        <div style="font-size:11px; font-weight:700; color:#0f172a;">🏢 Apartments</div>
                        <div style="font-size:16px; font-weight:800; color:#16a34a; margin:2px 0;">{_fmt(margin_apt)}</div>
                        <div style="font-size:10px; color:#64748b; font-weight:500;">Acq Stock: {n_apt}</div>
                    </div>
                </td>
                <td style="width:50%; padding:0 0 0 4px;">
                    <div style="background:{vil_bg}; border:1px solid {vil_brd}; border-radius:6px; padding:8px;">
                        <div style="font-size:11px; font-weight:700; color:#0f172a;">🏡 Villas/Houses</div>
                        <div style="font-size:16px; font-weight:800; color:#16a34a; margin:2px 0;">{_fmt(margin_villa)}</div>
                        <div style="font-size:10px; color:#64748b; font-weight:500;">Acq Stock: {n_vil}</div>
                    </div>
                </td>
            </tr>
        </table>
    """

    # --- Micro-Charts (Performance Indices) ---
    def _bar(label, val, color):
        pct = int(min(val * 100, 100))
        # Use highly compatible flat CSS for Google Earth KML engine
        return f"""
        <div style="margin-bottom:8px; display:block;">
            <table style="width:100%; border-collapse:collapse; margin-bottom:4px;"><tr>
                <td style="font-size:11px; font-weight:600; color:#0f172a;">{label}</td>
                <td style="text-align:right; font-size:11px; font-weight:800; color:{color};">{val:.2f}</td>
            </tr></table>
            <div style="width:100%; height:8px; background-color:#e2e8f0; display:block;">
                <div style="width:{pct}%; height:8px; background-color:{color}; display:block;"></div>
            </div>
        </div>"""

    html += f"""
    <div style="background:#f8fafc; border:1px solid #e2e8f0; border-radius:8px; padding:12px; margin-bottom:16px;">
        <div style="font-size:10px; font-weight:800; color:#64748b; text-transform:uppercase; letter-spacing:1px; margin-bottom:10px; display:flex; justify-content:space-between;">
            <span>Performance Indices</span>
            <span style="color:#94a3b8;">OSM Conf: {osm_conf:.2f}</span>
        </div>
        {_bar('Demand Intensity', demand, '#f59e0b')}
        {_bar('Supply Feasibility', supply_idx, '#3b82f6')}
        {_bar('Transit Proximity', transit, '#0ea5e9')}
        {_bar('Employment Gravity', employment, '#8b5cf6')}
        {_bar('Lifestyle Density', lifestyle, '#ec4899')}
    </div>"""

    # --- Spillover & Footer ---
    if aura != 1.0:
        aura_bg = '#fef2f2' if aura < 1 else '#f0fdfa'
        aura_border = '#fecaca' if aura < 1 else '#ccfbf1'
        aura_icon = '⚠️' if aura < 1 else '✨'
        html += f"""
    <div style="background:{aura_bg}; border-top:1px solid {aura_border}; padding:10px 20px;">
        <table style="width:100%; border-collapse:collapse;"><tr>
            <td style="width:24px; vertical-align:top; font-size:16px; padding-top:2px;">{aura_icon}</td>
            <td>
                <div style="font-size:12px; font-weight:700; color:#0f172a;">Spatial Spillover <span style="color:{'#14b8a6' if aura>1 else '#ef4444'};">({aura_str})</span></div>
                <div style="font-size:10px; color:#64748b; font-weight:500; margin-top:2px;">{aura_src}</div>
            </td>
        </tr></table>
    </div>"""

    html += f"""
    <div style="background:#f1f5f9; border-top:1px solid #e2e8f0; padding:8px 20px; display:flex; justify-content:space-between; align-items:center;">
        <div style="font-size:10px; color:#64748b; font-weight:600;">{sample} raw listings</div>
        <div style="font-size:10px; color:#94a3b8; font-weight:500;">Flent Lens 2.0 Engine ⚡</div>
    </div>
    </div>"""
    return html


# ═══════════════════════════════════════════════════════════════════
# KML EXPORT
# ═══════════════════════════════════════════════════════════════════
def export_investment_atlas_kml(hex_df, hex_full_gdf, listings_gdf, osm_data=None,
                                 filename=None):
    filename = filename or f'{config.CITY_NAME}_Investment_Atlas.kml'
    with log_process(f"Building {config.CITY_NAME} Investment Atlas KML"):
        kml, doc = _kml_doc(f"Flent Lens 2.0 — {config.CITY_NAME} Investment Atlas")
        ET.SubElement(doc, _e('description')).text = (
            f"H3 Res {config.H3_RESOLUTION} Hex Grid | "
            f"Generated {datetime.now().strftime('%Y-%m-%d %H:%M')}")

        tc_html = {'Tier 1': '#1a8c38', 'Tier 2': '#d4a017', 'Tier 3': '#c0392b', 'Excluded': '#7f8c8d'}
        tier_cfg = {
            'Tier 1': {'line': 'FF258c1a', 'poly': 'B21bc455'},
            'Tier 2': {'line': 'FF17a0d4', 'poly': 'B2FFD417'},
            'Tier 3': {'line': 'FF2b39c0', 'poly': 'B24e70E8'},
            'Excluded': {'line': 'FF8d8c7f', 'poly': '50A5A5A5'},
        }
        for t, c in tier_cfg.items():
            _add_style(doc, f"poly_{t.replace(' ', '')}", c['line'], c['poly'])

        _add_icon_style(doc, 'pin_top', 'http://maps.google.com/mapfiles/kml/shapes/star.png', '1.2')

        merged = hex_full_gdf.copy()

        # Layer 1: Hex polygons
        layer1 = ET.SubElement(doc, _e('Folder'))
        ET.SubElement(layer1, _e('name')).text = "🗺️ Hex Tier Map"
        ET.SubElement(layer1, _e('open')).text = "1"
        for tn in ['Tier 1', 'Tier 2', 'Tier 3', 'Excluded']:
            sub = merged[merged['tier'] == tn]
            if len(sub) == 0: continue
            sf = ET.SubElement(layer1, _e('Folder'))
            ET.SubElement(sf, _e('name')).text = f"{tn} ({len(sub)} hexes)"
            for _, r in sub.iterrows():
                pm = ET.SubElement(sf, _e('Placemark'))
                ET.SubElement(pm, _e('name')).text = str(r.get('hex_name', r['hex_id'][:10]))
                ET.SubElement(pm, _e('styleUrl')).text = f"#poly_{tn.replace(' ', '')}"
                ET.SubElement(pm, _e('description')).text = _hex_popup(r, tc_html)
                geom = r.geometry
                if geom.geom_type == 'Polygon':
                    _add_polygon(pm, geom)
                elif geom.geom_type == 'MultiPolygon':
                    mg = ET.SubElement(pm, _e('MultiGeometry'))
                    for poly in geom.geoms: _add_polygon(mg, poly)
        print_detail(f"Layer 1: {len(merged)} hex polygons")

        # Layer 2: Top 10 stars
        layer2 = ET.SubElement(doc, _e('Folder'))
        ET.SubElement(layer2, _e('name')).text = "🏆 Top 10 Priority Targets"
        ET.SubElement(layer2, _e('open')).text = "1"
        top10 = merged[merged['tier'] == 'Tier 1'].sort_values('OPP_SCORE', ascending=False).head(10)
        if len(top10) == 0: top10 = merged.sort_values('OPP_SCORE', ascending=False).head(10)
        for rank, (_, r) in enumerate(top10.iterrows(), 1):
            pm = ET.SubElement(layer2, _e('Placemark'))
            ET.SubElement(pm, _e('name')).text = f"#{rank}  {r.get('hex_name', '')}"
            ET.SubElement(pm, _e('styleUrl')).text = "#pin_top"
            ET.SubElement(pm, _e('description')).text = f"<b>Rank #{rank}</b><br/>" + _hex_popup(r, tc_html)
            cen = r.geometry.centroid
            pt = ET.SubElement(pm, _e('Point'))
            ET.SubElement(pt, _e('coordinates')).text = f"{cen.x},{cen.y},0"

        # Layer 3: Infrastructure Summary (Aggregated at Centroids)
        if osm_data:
            osm_layer = ET.SubElement(doc, _e('Folder'))
            ET.SubElement(osm_layer, _e('name')).text = "📊 Infrastructure Summary"
            ET.SubElement(osm_layer, _e('open')).text = "0"

            # Group POIs for calculation
            work_pts = np.array([[p['lat'], p['lon']] for p in osm_data.get('offices', []) + osm_data.get('commercial', [])])
            tran_pts = np.array([[p['lat'], p['lon']] for p in osm_data.get('metro_stations', []) + osm_data.get('bus_stops', [])])
            life_pts = np.array([[p['lat'], p['lon']] for p in osm_data.get('cafes', []) + osm_data.get('gyms', []) + osm_data.get('supermarkets', [])])

            _add_icon_style(doc, 'pin_infra', 'http://maps.google.com/mapfiles/kml/shapes/info-i.png', '1.0')

            def _fast_count(pts, lat, lon, radius_km=2.0):
                if len(pts) == 0: return 0
                dlat = pts[:,0] - lat
                dlon = pts[:,1] - lon
                # Quick haversine approximation
                dist = np.sqrt((dlat * 111.32)**2 + (dlon * 111.32 * np.cos(np.radians(lat)))**2)
                return int((dist <= radius_km).sum())

            for _, r in merged.iterrows():
                cen = r.geometry.centroid
                
                nw = _fast_count(work_pts, cen.y, cen.x)
                nt = _fast_count(tran_pts, cen.y, cen.x)
                nl = _fast_count(life_pts, cen.y, cen.x)
                
                if (nw + nt + nl) == 0: continue

                pm = ET.SubElement(osm_layer, _e('Placemark'))
                ET.SubElement(pm, _e('name')).text = f"📍 Infra: {r.get('hex_name', '')}"
                ET.SubElement(pm, _e('styleUrl')).text = "#pin_infra"
                
                desc = f"""
                <div style="width:250px; font-family:sans-serif; padding:10px;">
                    <b style="font-size:14px; color:#1e293b;">Local Infrastructure Summary</b><br/>
                    <div style="color:#64748b; font-size:12px; margin-bottom:10px;">Within 2km radius</div>
                    <table style="width:100%; border-collapse:collapse;">
                        <tr style="border-bottom:1px solid #e2e8f0;">
                            <td style="padding:6px 0;">🏢 Workplaces</td>
                            <td style="text-align:right; font-weight:700; color:#0f172a;">{nw}</td>
                        </tr>
                        <tr style="border-bottom:1px solid #e2e8f0;">
                            <td style="padding:6px 0;">🚇 Transit Hubs</td>
                            <td style="text-align:right; font-weight:700; color:#0f172a;">{nt}</td>
                        </tr>
                        <tr style="border-bottom:1px solid #e2e8f0;">
                            <td style="padding:6px 0;">☕ Lifestyle</td>
                            <td style="text-align:right; font-weight:700; color:#0f172a;">{nl}</td>
                        </tr>
                    </table>
                    <div style="margin-top:10px; font-size:11px; color:#94a3b8;">
                        Total Amenities: {nw+nt+nl}
                    </div>
                </div>
                """
                ET.SubElement(pm, _e('description')).text = desc
                pt = ET.SubElement(pm, _e('Point'))
                ET.SubElement(pt, _e('coordinates')).text = f"{cen.x},{cen.y},0"

        path = os.path.join(config.OUTPUT_DIR, filename)
        os.makedirs(config.OUTPUT_DIR, exist_ok=True)
        _save_kml(kml, path)
        print_success(f"KML Atlas → {os.path.basename(path)}")
        return path


# ═══════════════════════════════════════════════════════════════════
# XLSX EXPORT (7 sheets)
# ═══════════════════════════════════════════════════════════════════
def export_lens_report_xlsx(hex_df, ols_model=None, moran=None, sar_model=None,
                              pca_weights=None, filename=None):
    filename = filename or f'{config.CITY_NAME}_Master_Report.xlsx'
    with log_process(f"Building {config.CITY_NAME} Master Report XLSX"):
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
        from openpyxl.utils import get_column_letter
        from openpyxl.formatting.rule import ColorScaleRule

        path = os.path.join(config.OUTPUT_DIR, filename)
        os.makedirs(config.OUTPUT_DIR, exist_ok=True)
        wb = Workbook()

        thin = Border(left=Side('thin', color='D5D5D5'), right=Side('thin', color='D5D5D5'),
                      top=Side('thin', color='D5D5D5'), bottom=Side('thin', color='D5D5D5'))
        hdr_font = Font(name='Aptos', bold=True, color='FFFFFF', size=11)
        cell_font = Font(name='Aptos', size=10)
        tier_fills = {'Tier 1': PatternFill('solid', fgColor='C6EFCE'), 'Tier 2': PatternFill('solid', fgColor='FFEB9C'),
                      'Tier 3': PatternFill('solid', fgColor='FFCCCC'), 'Excluded': PatternFill('solid', fgColor='EEEEEE')}

        def write_sheet(ws, df, cols, labels, bg='1F4E79'):
            hfill = PatternFill('solid', fgColor=bg)
            for ci, h in enumerate(labels, 1):
                c = ws.cell(row=1, column=ci, value=h)
                c.font = hdr_font; c.fill = hfill; c.border = thin
                c.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
            for ri, (_, row) in enumerate(df.iterrows(), 2):
                for ci, col in enumerate(cols, 1):
                    v = _np(row.get(col, ''))
                    c = ws.cell(row=ri, column=ci, value=v)
                    c.font = cell_font; c.border = thin
                    if col == 'tier' and v in tier_fills:
                        c.fill = tier_fills[v]
            for ci in range(1, len(labels) + 1):
                ws.column_dimensions[get_column_letter(ci)].width = 16
            ws.freeze_panes = 'A2'

        # Sheet 0: Metadata
        ws0 = wb.active; ws0.title = "📋 Run Metadata"; ws0.sheet_properties.tabColor = '1F4E79'
        meta = [("City", config.CITY_NAME), ("Timestamp", datetime.now().isoformat()),
                ("H3 Resolution", config.H3_RESOLUTION), ("K-Ring", config.KRING_RADIUS),
                ("Smoothing β", config.KRING_DECAY_BETA), ("DDF Apartment", config.DDF_APARTMENT),
                ("DDF Villa", config.DDF_VILLA), ("PCA Weights", config.USE_PCA_WEIGHTS),
                ("Total Listings", int(hex_df['sample_size'].sum())),
                ("Total Hexes", len(hex_df)),
                ("Viable Hexes", int(hex_df['margin_viable'].sum()))]
        for ri, (k, v) in enumerate(meta, 1):
            ws0.cell(row=ri, column=1, value=k).font = Font(name='Aptos', bold=True)
            ws0.cell(row=ri, column=2, value=str(v))
        ws0.column_dimensions['A'].width = 24; ws0.column_dimensions['B'].width = 40

        # Sheet 1: Executive Summary (Top 10)
        ws1 = wb.create_sheet("🏆 Top 10"); ws1.sheet_properties.tabColor = '00B050'
        top10 = hex_df[hex_df['tier'] == 'Tier 1'].sort_values('OPP_SCORE', ascending=False).head(10)
        if len(top10) == 0: top10 = hex_df.sort_values('OPP_SCORE', ascending=False).head(10)
        cols1 = ['hex_name', 'tier', 'OPP_SCORE', 'arb_margin_best', 'best_asset_type',
                 'avg_rent_1bhk', 'Neff', 'stability_score', 'demand_intensity_idx']
        write_sheet(ws1, top10, cols1, ['Zone', 'Tier', 'Score', 'Margin (₹)', 'Asset',
                                         '1BHK Rent', 'Neff', 'Stability', 'Demand'], bg='00B050')

        # Sheet 2: Supply Profiling
        ws2 = wb.create_sheet("📊 Supply Profile"); ws2.sheet_properties.tabColor = '7030A0'
        cols2 = ['hex_name', 'cnt_1bhk', 'cnt_2bhk', 'cnt_3bhk', 'cnt_4bhk',
                 'n_apartments', 'n_villas', 'median_rent_1bhk', 'q1_rent_3bhk_apt',
                 'q1_rent_villa', 'median_sqft', 'pct_3bhk_large']
        labels2 = ['Zone', '1BHK#', '2BHK#', '3BHK#', '4BHK#', 'Apts', 'Villas',
                    'Med 1BHK', 'Q1 3BHK', 'Q1 Villa', 'Med Sqft', '%Large']
        write_sheet(ws2, hex_df.sort_values('total_listings', ascending=False), cols2, labels2, bg='7030A0')

        # Sheet 3: Full Hex Dataset
        ws3 = wb.create_sheet("📈 Full Dataset"); ws3.sheet_properties.tabColor = '1F4E79'
        full_cols = ['hex_id', 'hex_name', 'tier', 'OPP_SCORE', 'sample_size', 'Neff',
                     'pct_neighbor_sourced', 'confidence', 'stability_score',
                     'avg_rent_1bhk', 'rent_1bhk_CI_low', 'rent_1bhk_CI_high',
                     'arb_margin_apartment', 'arb_margin_villa', 'arb_margin_best', 'best_asset_type',
                     'demand_intensity_idx', 'supply_depth_idx',
                     'transit_score', 'employment_score', 'lifestyle_score', 'osm_confidence',
                     'aura_multiplier', 'centroid_lat', 'centroid_lon']
        avail = [c for c in full_cols if c in hex_df.columns]
        write_sheet(ws3, hex_df.sort_values('OPP_SCORE', ascending=False), avail, avail)

        # Sheet 4: DDF Sensitivity
        ws4 = wb.create_sheet("🔬 DDF Sensitivity"); ws4.sheet_properties.tabColor = 'FF6600'
        top_hexes = top10[['hex_name', 'avg_rent_1bhk', 'q1_rent_3bhk_apt', 'median_sqft']].copy()
        sens_rows = []
        for _, r in top_hexes.iterrows():
            for ddf_val in config.DDF_SENSITIVITY_RANGE:
                rooms = 3 if (r.get('median_sqft', 0) or 0) < 1400 else 4
                revenue = (r.get('avg_rent_1bhk', 0) or 0) * ddf_val * rooms
                acq = r.get('q1_rent_3bhk_apt', 0) or 0
                margin = revenue - acq
                sens_rows.append({'Zone': r['hex_name'], 'DDF': ddf_val, 'Rooms': rooms,
                                  'Revenue': revenue, 'Acq Cost': acq, 'Margin': margin})
        sens_df = pd.DataFrame(sens_rows)
        if len(sens_df) > 0:
            write_sheet(ws4, sens_df, sens_df.columns.tolist(), sens_df.columns.tolist(), bg='FF6600')

        # Sheet 5: Weight Calibration
        ws5 = wb.create_sheet("⚖️ Weights"); ws5.sheet_properties.tabColor = '333333'
        r = 1
        if pca_weights:
            for index_name, weights in pca_weights.items():
                if weights is None: continue
                ws5.cell(row=r, column=1, value=index_name).font = Font(name='Aptos', bold=True, size=12)
                r += 1
                for feat, w in weights.items():
                    ws5.cell(row=r, column=1, value=feat)
                    ws5.cell(row=r, column=2, value=round(w, 4))
                    r += 1
                r += 1
        ws5.column_dimensions['A'].width = 30; ws5.column_dimensions['B'].width = 16

        # Sheet 6: Data Quality
        ws6 = wb.create_sheet("📊 Data Quality"); ws6.sheet_properties.tabColor = 'C00000'
        dq_cols = ['hex_name', 'sample_size', 'Neff', 'pct_neighbor_sourced', 'confidence',
                   'stability_score', 'osm_confidence']
        dq_avail = [c for c in dq_cols if c in hex_df.columns]
        write_sheet(ws6, hex_df.sort_values('Neff', ascending=True), dq_avail, dq_avail, bg='C00000')

        wb.save(path)
        print_success(f"XLSX Report → {os.path.basename(path)} (7 sheets)")
        return path


# ═══════════════════════════════════════════════════════════════════
# GEOJSON EXPORT
# ═══════════════════════════════════════════════════════════════════
def export_hex_geojson(hex_full_gdf, filename=None):
    filename = filename or f'{config.CITY_NAME}_hex_analysis.geojson'
    with log_process("Exporting GeoJSON"):
        path = os.path.join(config.OUTPUT_DIR, filename)
        os.makedirs(config.OUTPUT_DIR, exist_ok=True)
        # Drop non-serializable columns
        export_gdf = hex_full_gdf.copy()
        for col in export_gdf.columns:
            if export_gdf[col].dtype == object:
                export_gdf[col] = export_gdf[col].astype(str)
        export_gdf.to_file(path, driver='GeoJSON')
        print_success(f"GeoJSON → {os.path.basename(path)}")
        return path


# ═══════════════════════════════════════════════════════════════════
# CITY SUMMARY JSON
# ═══════════════════════════════════════════════════════════════════
def export_city_summary(hex_df, moran=None, ols_model=None, sar_model=None):
    with log_process("Writing city_summary.json"):
        viable = hex_df[hex_df['margin_viable']]
        summary = {
            'city': config.CITY_NAME,
            'city_key': config.CITY_KEY,
            'run_timestamp': datetime.now().isoformat(),
            'h3_resolution': config.H3_RESOLUTION,
            'total_listings': int(hex_df['sample_size'].sum()),
            'total_hexes': len(hex_df),
            'viable_hexes': len(viable),
            'tier1_count': int((hex_df['tier'] == 'Tier 1').sum()),
            'tier2_count': int((hex_df['tier'] == 'Tier 2').sum()),
            'median_arb_margin': float(viable['arb_margin_best'].median()) if len(viable) > 0 else 0,
            'max_arb_margin': float(viable['arb_margin_best'].max()) if len(viable) > 0 else 0,
            'median_1bhk_rent': float(hex_df['avg_rent_1bhk'].median()) if hex_df['avg_rent_1bhk'].notna().any() else 0,
            'moran_i': float(moran.I) if moran else None,
            'moran_p': float(moran.p_sim) if moran else None,
            'ols_slope': float(ols_model.params[1]) if ols_model else None,
            'ols_r2': float(ols_model.rsquared) if ols_model else None,
            'sar_rho': float(sar_model.betas[-1][0]) if sar_model else None,
            'pct_villa_wins': float((viable['best_asset_type'] == 'villa').mean() * 100) if len(viable) > 0 else 0,
        }
        path = os.path.join(config.OUTPUT_DIR, 'city_summary.json')
        os.makedirs(config.OUTPUT_DIR, exist_ok=True)
        with open(path, 'w') as f:
            json.dump(summary, f, indent=2, default=str)
        print_success(f"city_summary.json → {os.path.basename(path)}")
        return summary


def load_cached_summaries():
    """Load city_summary.json from all city output dirs."""
    from city_config import CITY_PROFILES, BASE_DIR
    summaries = []
    for key in CITY_PROFILES:
        path = os.path.join(BASE_DIR, 'output', key, 'city_summary.json')
        if os.path.exists(path):
            with open(path) as f:
                summaries.append(json.load(f))
    return summaries


def export_cross_city(summaries):
    """Generate cross-city comparison outputs with Expansion Ranking & Master KML."""
    with log_process("Building cross-city comparators"):
        if not summaries:
            print_warning("No city summaries available")
            return
            
        output_dir = os.path.join(os.path.dirname(config.OUTPUT_DIR), 'cross_city')
        os.makedirs(output_dir, exist_ok=True)

        # 1. Excel Expansion Ranker
        df = pd.DataFrame(summaries)
        
        # Calculate Heuristic Score (Tier 1 Volume + Financial Yield Arbitrage Margin)
        # e.g., 10 Tier1 hexes * 10,000 + 15,000 margin = 115,000 score
        df['flent_score'] = (df.get('tier1_count', 0) * 10000) + df.get('median_arb_margin', 0)
        df_sorted = df.sort_values('flent_score', ascending=False).reset_index(drop=True)
        
        # Assign Priority Badges
        ranks = []
        for i in range(len(df_sorted)):
            if i == 0: ranks.append("🏆 HQ PRIORITY 1")
            elif i == 1: ranks.append("🥈 PRIORITY 2")
            elif i == 2: ranks.append("🥉 PRIORITY 3")
            else: ranks.append(f"Rank {i+1}")
        df_sorted.insert(0, 'expansion_rank', ranks)
        
        # Save Sorted Database
        excel_path = os.path.join(output_dir, 'India_Expansion_Master.xlsx')
        df_sorted.to_excel(excel_path, index=False)
        print_success(f"Expansion Ranker → India_Expansion_Master.xlsx ({len(df)} cities)")

        # 2. India Master KML Generator (Network Link Architecture)
        from src.utils.exporter import _kml_doc, _e, _save_kml
        kml, doc = _kml_doc("Flent Lens 2.0 — India Master Atlas")
        ET.SubElement(doc, _e('description')).text = f"Master View aggregating {len(df)} localized city grids via NetworkLinks."
        
        # We need absolute path or relative path to the city KMLs. Relative is safer for distribution.
        # This file is in `output/cross_city/`. The local KML is in `output/{city}/...`
        # So relative path = `../{city}/{city_name}_Investment_Atlas.kml`
        for _, row in df_sorted.iterrows():
            city_key = row['city_key']
            city_title = row['city']
            
            nl = ET.SubElement(doc, _e('NetworkLink'))
            ET.SubElement(nl, _e('name')).text = f"🌐 {city_title} Topology Layer"
            ET.SubElement(nl, _e('visibility')).text = "1"
            ET.SubElement(nl, _e('flyToView')).text = "0"
            link = ET.SubElement(nl, _e('Link'))
            # Pathing mapping correctly back into root output dir
            ET.SubElement(link, _e('href')).text = f"../{city_key}/{city_title}_Investment_Atlas.kml"
            
        kml_path = os.path.join(output_dir, 'India_Master_Atlas.kml')
        _save_kml(kml, kml_path)
        print_success(f"Master Topography Map → India_Master_Atlas.kml")

# EOF
