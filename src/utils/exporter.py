"""
Flent Lens — Export Engine (v2)
Two clean deliverables:
  1. flent_investment_atlas.kml  — Layered Google Earth map
  2. flent_lens_report.xlsx      — 4-sheet Excel workbook for leadership
"""
import os
import pandas as pd
import geopandas as gpd
import numpy as np
import xml.etree.ElementTree as ET
from datetime import datetime
import config
from src.utils.logger import print_success, print_warning, print_detail, log_process

# ═══════════════════════════════════════════════════════════════════
# REPORT COLUMN SCHEMA
# ═══════════════════════════════════════════════════════════════════
REPORT_COLUMNS = [
    'ward_id', 'ward_name', 'tier', 'OPP_SCORE',
    'cnt_1bhk', 'cnt_2bhk', 'cnt_3bhk', 'cnt_4bhk',
    'avg_rent_1bhk', 'avg_rent_3bhk', 'avg_rent_4bhk',
    'avg_sqft_1bhk', 'avg_sqft_3bhk',
    'arb_margin_3bhk', 'arb_margin_4bhk', 'arb_margin_best',
    'arb_margin_pct', 'margin_viable', 'margin_density',
    'price_pressure', 'sfc', 'demand_intensity_idx',
    'pct_3bhk_xl', 'supply_depth_idx',
    'transit_score', 'sez_employment_score',
    'rps_1bhk', 'rps_3bhk', 'psf_diff',
    'aura_multiplier', 'data_sparse', 'demand_discount',
]

COLUMN_LABELS = {
    'ward_id': 'Ward ID', 'ward_name': 'Ward Name', 'tier': 'Investment Tier',
    'OPP_SCORE': 'Opp Score',
    'cnt_1bhk': '1BHK #', 'cnt_2bhk': '2BHK #',
    'cnt_3bhk': '3BHK #', 'cnt_4bhk': '4BHK #',
    'avg_rent_1bhk': '1BHK Rent (₹)', 'avg_rent_3bhk': '3BHK Acq Cost (₹)',
    'avg_rent_4bhk': '4BHK Acq Cost (₹)',
    'avg_sqft_1bhk': '1BHK Sqft', 'avg_sqft_3bhk': '3BHK Sqft',
    'arb_margin_3bhk': '3BHK Margin (₹)', 'arb_margin_4bhk': '4BHK Margin (₹)',
    'arb_margin_best': 'Average Margin (₹)', 'arb_margin_pct': 'Margin %',
    'margin_viable': 'Viable', 'margin_density': 'Margin Density',
    'price_pressure': 'Price Pressure', 'sfc': 'Small Flat Conc.',
    'demand_intensity_idx': 'Demand Index', 'pct_3bhk_xl': '% XL 3BHK',
    'supply_depth_idx': 'Supply Index', 'transit_score': 'Transit Score',
    'sez_employment_score': 'SEZ Score', 'rps_1bhk': '₹/sqft 1BHK',
    'rps_3bhk': '₹/sqft 3BHK', 'psf_diff': 'PSF Δ',
    'aura_multiplier': 'Aura Mult.', 'data_sparse': 'Data Sparse',
    'demand_discount': 'Demand Discount',
}


def _pick(df, cols):
    return df[[c for c in cols if c in df.columns]].copy()

def _fmt(val):
    try:
        return f"₹{val:,.0f}"
    except (ValueError, TypeError):
        return str(val)

def _np_clean(val):
    if isinstance(val, np.integer):   return int(val)
    if isinstance(val, np.floating):  return float(val)
    if isinstance(val, np.bool_):     return bool(val)
    return val


# ═══════════════════════════════════════════════════════════════════
# KML HELPERS
# ═══════════════════════════════════════════════════════════════════
KNS = "http://www.opengis.net/kml/2.2"

def _e(tag):
    return f'{{{KNS}}}{tag}'

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
        f"{coord[0]},{coord[1]},0" for coord in polygon.exterior.coords)
    for interior in polygon.interiors:
        ib = ET.SubElement(pe, _e('innerBoundaryIs'))
        lr2 = ET.SubElement(ib, _e('LinearRing'))
        ET.SubElement(lr2, _e('coordinates')).text = " ".join(
            f"{coord[0]},{coord[1]},0" for coord in interior.coords)

def _save_kml(kml, path):
    os.makedirs(os.path.dirname(path) if os.path.dirname(path) else '.', exist_ok=True)
    ET.ElementTree(kml).write(path, xml_declaration=True, encoding='utf-8')


def _q_score(val):
    v = float(val)
    if v >= 80: return f"{v:.1f} (Elite)"
    if v >= 60: return f"{v:.1f} (Strong)"
    if v >= 40: return f"{v:.1f} (Moderate)"
    return f"{v:.1f} (Weak)"

def _q_idx(val, t1, t2, l1, l2, l3):
    v = float(val)
    if v >= t1: return f"{v:.2f} ({l1})"
    if v >= t2: return f"{v:.2f} ({l2})"
    return f"{v:.2f} ({l3})"

# ═══════════════════════════════════════════════════════════════════
# WARD POPUP HTML — shared by both layers
# ═══════════════════════════════════════════════════════════════════
def _ward_popup(r, tier_colors):
    wn   = str(r.get('ward_name', r['ward_id']))
    tier = r.get('tier', 'Excluded')
    
    # 1. Colors and Badges
    tc   = tier_colors.get(tier, '#94a3b8')
    bg_header = '#0f172a'
    
    # 2. Extract Data
    score = r.get('OPP_SCORE', 0)
    data_sparse = bool(r.get('data_sparse', False))
    margin_density = r.get('margin_density', 0)
    margin = r.get('arb_margin_best', 0)
    area = r.get('area_sqkm', 1.0)
    
    def _i(k): 
        v = r.get(k, 0)
        return int(float(v)) if pd.notna(v) and v is not None else 0
    def _f(k):
        v = r.get(k, 0)
        return float(v) if pd.notna(v) and v is not None else 0.0

    psf_diff = _f('psf_diff')
    rps_1bhk = _f('rps_1bhk')
    rps_3bhk = _f('rps_3bhk')
    rent_1 = _f('avg_rent_1bhk')
    psf_diff_pct = (psf_diff / rps_1bhk * 100) if rps_1bhk > 0 else 0
    demand_discount = _f('demand_discount')
        
    supply = _i('cnt_3bhk') + _i('cnt_4bhk')
    pct_xl = _f('pct_3bhk_xl') * 100
    
    q1_rent = _f('q1_avg_rent'); q1_c = _i('q1_count')
    tam_units = q1_c
    q2_rent = _f('q2_avg_rent'); q2_c = _i('q2_count')
    q3_rent = _f('q3_avg_rent'); q3_c = _i('q3_count')
    q4_rent = _f('q4_avg_rent'); q4_c = _i('q4_count')
    
    demand = _f('demand_intensity_idx')
    transit = _f('transit_score')
    sez = _f('sez_employment_score')
    closest_sezs = r.get('closest_sezs', 'No SEZ data available.')
    aura = _f('aura_multiplier') if _f('aura_multiplier') > 0 else 1.0
    aura_sources = r.get('aura_sources', 'None')
    if pd.isna(aura_sources): aura_sources = 'None'
    aura_str = f"+{(aura-1)*100:.1f}% Spatial Boost" if aura > 1.0 else (f"{(aura-1)*100:.1f}% Penalty" if aura < 1.0 else "No Boost")
    
    margin_density = _f('margin_density')
    margin = _f('arb_margin_best')
    area = _f('area_sqkm') if _f('area_sqkm') > 0 else 1.0
    
    # 3. Format strings
    def F1(x): return f"₹{x/1000000:.1f}M" if x >= 1000000 else f"₹{x:,.0f}"
    def Fk(x): return f"₹{x/1000:.0f}k" if x > 0 else "N/A"
    
    # 4. Build HTML
    html = f"""<div style="width: 380px; background: white; border: 1px solid #cbd5e1; box-shadow: 0 10px 25px -5px rgba(0,0,0,0.1); border-radius: 8px; overflow: hidden; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">"""
    
    html += f"""
    <div style="background: {bg_header}; padding: 14px 16px;">
        <table style="width:100%; border-collapse:collapse;">
            <tr>
                <td>
                    <h3 style="margin:0 0 4px 0; font-size:18px; color: white;">{wn}</h3>
                    <span style="background:{tc}; color:white; padding:2px 6px; border-radius:4px; font-size:11px; font-weight:600; text-transform:uppercase;">{tier}</span>
                </td>
                <td style="text-align:right;">
                    <div style="font-size:24px; font-weight:bold; color: {tc};">{score:.1f}</div>
                    <div style="font-size:10px; color:#cbd5e1; text-transform:uppercase;">Opp Score</div>
                </td>
            </tr>
        </table>
    </div>"""

    if data_sparse:
        html += """
    <div style="background: #fef08a; padding: 6px 16px; border-bottom: 1px solid #fde047;">
        <div style="font-size: 11px; color:#854d0e; font-weight:bold;">⚠️ Low Data Confidence</div>
        <div style="font-size: 10px; color:#a16207;">Margins projected on &lt; 5 active listings. High variance risk.</div>
    </div>"""

    html += f"""
    <div style="padding: 12px 16px 0 16px;">
        <div style="font-size:10px; font-weight:700; color:#94a3b8; text-transform:uppercase; letter-spacing:0.5px; border-bottom: 1px solid #e2e8f0; padding-bottom: 4px; margin-bottom: 8px;">Core Arbitrage Thesis</div>
        <table style="width:100%; border-collapse:collapse; margin-bottom: 12px;">
            <tr>
                <td style="width:50%; vertical-align:top; border-right: 1px solid #f1f5f9; padding-right:12px; padding-bottom: 10px;">
                    <div style="font-size: 10px; color: #64748b; font-weight: 600;">Margin Density (TAM)</div>
                    <div style="font-size: 16px; font-weight: bold; color: #0284c7; margin-bottom: 2px;">{F1(margin_density)} / km²</div>
                    <div style="font-size: 8px; font-family: monospace; color: #0284c7; background: #f0f9ff; border: 1px solid #bae6fd; border-radius: 3px; padding: 2px 4px; margin-bottom: 4px; display: inline-block;">
                        ({Fk(margin)} × {tam_units} Q1 units) ÷ {area:.1f} km²
                    </div>
                    <div style="font-size: 9px; color: #94a3b8; line-height: 1.2;">Realistic addressable pool if <i>all Q1 (bottom 25%)</i> stock acquired.</div>
                </td>
                <td style="width:50%; vertical-align:top; padding-left:12px; padding-bottom: 10px;">
                    <div style="font-size: 10px; color: #64748b; font-weight: 600;">Average Arb Margin</div>
                    <div style="font-size: 16px; font-weight: bold; color: #16a34a; margin-bottom: 2px;">{_fmt(margin)} <span style="font-size:11px;color:#94a3b8;">/mo</span></div>
                    <div style="font-size: 9px; color: #94a3b8; line-height: 1.2;">Yield margin per flat after conversion & discount.</div>
                </td>
            </tr>
            <tr>
                <td style="width:50%; vertical-align:top; border-right: 1px solid #f1f5f9; padding-right:12px; padding-top: 10px; border-top: 1px solid #f1f5f9;">
                    <div style="font-size: 10px; color: #64748b; font-weight: 600;">1BHK Median Rent</div>
                    <div style="font-size: 16px; font-weight: bold; color: #0f172a; margin-bottom: 2px;">{_fmt(rent_1)} <span style="font-size:11px;color:#94a3b8;">/mo</span></div>
                    <div style="font-size: 9px; color: #94a3b8; line-height: 1.2;">Retail rent baseline for standard 1BHK.</div>
                </td>
                <td style="width:50%; vertical-align:top; padding-left:12px; padding-top: 10px; border-top: 1px solid #f1f5f9;">
                    <div style="font-size: 10px; color: #64748b; font-weight: 600;">Demand Discount</div>
                    <div style="font-size: 16px; font-weight: bold; color: #0284c7; margin-bottom: 2px;">{demand_discount * 100:.1f}%</div>
                    <div style="font-size: 9px; color: #94a3b8; line-height: 1.2;">Elastic multiplier based on ward price pressure.</div>
                </td>
            </tr>
        </table>
        
        <div style="font-size:10px; font-weight:700; color:#94a3b8; text-transform:uppercase; letter-spacing:0.5px; border-bottom: 1px solid #e2e8f0; padding-bottom: 4px; margin-bottom: 8px;">Supply Depth</div>
        <table style="width:100%; border-collapse:collapse; margin-bottom:12px;">
            <tr>
                <td style="font-size:12px; color:#475569; padding-bottom:6px;">Available 3BHK+ Stock:</td>
                <td style="font-size:12px; font-weight:bold; text-align:right; padding-bottom:6px;">{supply} Units</td>
            </tr>
            <tr>
                <td colspan="2">
                    <table style="width:100%; border-collapse:collapse; text-align:center; border-radius:4px; overflow:hidden;">
                        <tr style="background:#f1f5f9;">
                            <td style="width:25%; border-right:1px solid #e2e8f0; padding:4px;"><div style="font-size:11px; font-weight:600; color:#475569;">Q1</div></td>
                            <td style="width:25%; border-right:1px solid #e2e8f0; padding:4px;"><div style="font-size:11px; font-weight:600; color:#475569;">Q2</div></td>
                            <td style="width:25%; border-right:1px solid #e2e8f0; padding:4px;"><div style="font-size:11px; font-weight:600; color:#475569;">Q3</div></td>
                            <td style="width:25%; padding:4px;"><div style="font-size:11px; font-weight:600; color:#475569;">Q4</div></td>
                        </tr>
                        <tr style="border:1px solid #e2e8f0; border-top:none;">
                            <td style="padding:6px 2px; border-right:1px solid #e2e8f0; background:rgba(34,197,94,0.05);"><div style="font-size:13px; font-weight:bold; color:#0f172a;">{Fk(q1_rent)}</div><div style="font-size:9px; color:#64748b;">({q1_c}u)</div></td>
                            <td style="padding:6px 2px; border-right:1px solid #e2e8f0; background:rgba(34,197,94,0.05);"><div style="font-size:13px; font-weight:bold; color:#0f172a;">{Fk(q2_rent)}</div><div style="font-size:9px; color:#64748b;">({q2_c}u)</div></td>
                            <td style="padding:6px 2px; border-right:1px solid #e2e8f0;"><div style="font-size:13px; font-weight:bold; color:#0f172a;">{Fk(q3_rent)}</div><div style="font-size:9px; color:#64748b;">({q3_c}u)</div></td>
                            <td style="padding:6px 2px;"><div style="font-size:13px; font-weight:bold; color:#0f172a;">{Fk(q4_rent)}</div><div style="font-size:9px; color:#64748b;">({q4_c}u)</div></td>
                        </tr>
                    </table>
                </td>
            </tr>
            <tr>
                <td colspan="2" style="padding-top:6px;">
                    <div style="font-size:10px; color:#94a3b8; line-height:1.2;">* {pct_xl:.0f}% of 3BHKs are >2000 sqft (XL) and will yield 4 rooms.</div>
                </td>
            </tr>
        </table>
"""
    d_val, d_label = (demand, _q_idx(demand, 0.5, 0.35, 'High', 'Mod', 'Low').split()[0])

    html += f"""
        <div style="font-size:10px; font-weight:700; color:#94a3b8; text-transform:uppercase; letter-spacing:0.5px; border-bottom: 1px solid #e2e8f0; padding-bottom: 4px; margin-bottom: 10px;">Market & Location Performance</div>
        <div style="margin-bottom:12px;">
            <table style="width:100%; border-collapse:collapse;">
                <tr><td style="font-size:11px; font-weight:600; color:#334155;">Demand Intensity</td><td style="text-align:right; font-size:11px; font-weight:bold; color:#0f172a;">{d_val:.2f} <span style="font-weight:normal;color:#64748b;">({d_label})</span></td></tr>
            </table>
            <div style="width:100%; height:4px; background:#e2e8f0; border-radius:2px; margin-top:4px; margin-bottom:2px;"><div style="width:{min(d_val*100, 100)}%; height:4px; background:#f59e0b; border-radius:2px;"></div></div>
            <div style="font-size:9px; color:#94a3b8;">Relative rent elasticity and low inventory time-on-market.</div>
        </div>"""

    # ── Transit section (only if transit data is available) ──
    if config.HAS_TRANSIT:
        t_val = transit
        t_label = _q_idx(transit, 0.75, 0.4, 'High', 'Good', 'Basic').split()[0]
        html += f"""
        <div style="margin-bottom:12px;">
            <table style="width:100%; border-collapse:collapse;">
                <tr><td style="font-size:11px; font-weight:600; color:#334155;">Transit Connectivity</td><td style="text-align:right; font-size:11px; font-weight:bold; color:#0f172a;">{t_val:.2f} <span style="font-weight:normal;color:#64748b;">({t_label})</span></td></tr>
            </table>
            <div style="width:100%; height:4px; background:#e2e8f0; border-radius:2px; margin-top:4px; margin-bottom:2px;"><div style="width:{min(t_val*100, 100)}%; height:4px; background:#0284c7; border-radius:2px;"></div></div>
            <div style="font-size:9px; color:#94a3b8;">Proxy access gravity to arterial bus and metro routes.</div>
        </div>"""

    # ── SEZ section (only if SEZ data is available) ──
    if config.HAS_SEZ:
        s_val = sez
        html += f"""
        <div style="background:#fff7ed; padding:10px; border-left:3px solid #f97316; border-radius:0 4px 4px 0; margin-bottom:14px;">
            <div style="font-size:11px; font-weight:600; color:#c2410c; margin-bottom:4px;">SEZ Employment Gravity Index: {s_val:.2f}</div>
            <div style="font-size:9px; color:#9a3412; margin-bottom:6px; line-height:1.2;">Proximity gravity modeling to major corporate parks. Nearest hubs:</div>
            {closest_sezs}
        </div>"""

    html += "</div>"

    if aura != 1.0:
        html += f"""
    <div style="background: #f8fafc; padding: 12px 16px; border-top: 1px solid #e2e8f0;">
        <table style="width:100%; border-collapse:collapse;">
            <tr>
                <td style="font-size:24px; text-align:center; padding-right:12px; width:10%;">✨</td>
                <td>
                    <div style="font-size:11px; font-weight:600; color:#334155;">{aura_str}</div>
                    <div style="font-size:10px; color:#64748b; margin-top:2px;">Spillover value inherited from neighbors: {aura_sources}</div>
                </td>
            </tr>
        </table>
    </div>"""

    html += "</div>"
    return html


# ═══════════════════════════════════════════════════════════════════
# CONSOLIDATED INVESTMENT ATLAS KML
# ═══════════════════════════════════════════════════════════════════
def export_investment_atlas_kml(df, wards_gdf, listings_gdf,
                                  filename='flent_investment_atlas.kml'):
    with log_process(f"Building {config.CITY_NAME} Investment Atlas KML"):
        kml, doc = _kml_doc(f"Flent Lens — {config.CITY_NAME} Investment Atlas")
        ET.SubElement(doc, _e('description')).text = (
            "Flent Lens Ward Opportunity Atlas | "
            f"Generated {datetime.now().strftime('%Y-%m-%d %H:%M')}")

        tier_colors_html = {
            'Tier 1': '#1a8c38', 'Tier 2': '#d4a017', 'Tier 3': '#c0392b', 'Excluded': '#7f8c8d'
        }
        # KML AABBGGRR
        tier_cfg = {
            'Tier 1':   {'line': 'FF258c1a', 'poly': 'B21bc455'},
            'Tier 2':   {'line': 'FF17a0d4', 'poly': 'B2FFD417'},
            'Tier 3':   {'line': 'FF2b39c0', 'poly': 'B24e70E8'},
            'Excluded': {'line': 'FF8d8c7f', 'poly': '50A5A5A5'},
        }
        for tier, c in tier_cfg.items():
            _add_style(doc, f"poly_{tier.replace(' ', '')}", c['line'], c['poly'], width='1.5')

        # Pin icons
        pin_icons = {
            'Tier 1':   ('pin_t1', 'http://maps.google.com/mapfiles/kml/paddle/grn-stars.png'),
            'Tier 2':   ('pin_t2', 'http://maps.google.com/mapfiles/kml/paddle/ylw-diamond.png'),
            'Tier 3':   ('pin_t3', 'http://maps.google.com/mapfiles/kml/paddle/red-diamond.png'),
            'Excluded': ('pin_ex', 'http://maps.google.com/mapfiles/kml/paddle/wht-diamond.png'),
            'top10':    ('pin_top', 'http://maps.google.com/mapfiles/kml/shapes/star.png'),
        }
        for key, (sid, href) in pin_icons.items():
            scale = '1.2' if key == 'top10' else '0.8'
            _add_icon_style(doc, sid, href, scale)

        _add_icon_style(doc, 'pin_3bhk', 'http://maps.google.com/mapfiles/kml/paddle/ylw-circle.png', '0.5')

        # Merge geometry from wards_gdf (drop names to avoid _x/_y collision)
        merged = wards_gdf[['ward_id', 'geometry']].merge(df, on='ward_id')

        # ── LAYER 1: Tier polygon choropleth ──────────────────
        layer1 = ET.SubElement(doc, _e('Folder'))
        ET.SubElement(layer1, _e('name')).text = "🗺️ Ward Tier Map"
        ET.SubElement(layer1, _e('open')).text = "1"

        for tier_name in ['Tier 1', 'Tier 2', 'Tier 3', 'Excluded']:
            sub = merged[merged['tier'] == tier_name]
            if len(sub) == 0:
                continue
            sub_folder = ET.SubElement(layer1, _e('Folder'))
            ET.SubElement(sub_folder, _e('name')).text = f"{tier_name} ({len(sub)} wards)"

            for _, r in sub.iterrows():
                pm = ET.SubElement(sub_folder, _e('Placemark'))
                # Priority: ward_name, then Name (from KML), then ward_id
                wn = str(r.get('ward_name', r.get('Name', r['ward_id'])))
                ET.SubElement(pm, _e('name')).text = wn
                ET.SubElement(pm, _e('styleUrl')).text = f"#poly_{tier_name.replace(' ', '')}"
                ET.SubElement(pm, _e('description')).text = _ward_popup(r, tier_colors_html)

                geom = r.geometry
                if geom.geom_type == 'Polygon':
                    _add_polygon(pm, geom)
                elif geom.geom_type == 'MultiPolygon':
                    mg = ET.SubElement(pm, _e('MultiGeometry'))
                    for poly in geom.geoms:
                        _add_polygon(mg, poly)

        print_detail(f"Layer 1: {len(merged)} ward polygons")

        # ── LAYER 2: Ward analytics centroid pins ──────────────
        layer2 = ET.SubElement(doc, _e('Folder'))
        ET.SubElement(layer2, _e('name')).text = "📍 Ward Analytics Pins"
        ET.SubElement(layer2, _e('visibility')).text = "0"

        for _, r in merged.iterrows():
            tier = r.get('tier', 'Excluded')
            pm = ET.SubElement(layer2, _e('Placemark'))
            ET.SubElement(pm, _e('name')).text = f"{r.get('ward_name', '')} [{r.get('OPP_SCORE', 0):.0f}]"
            ET.SubElement(pm, _e('styleUrl')).text = f"#{pin_icons.get(tier, pin_icons['Excluded'])[0]}"
            ET.SubElement(pm, _e('description')).text = _ward_popup(r, tier_colors_html)
            cen = r.geometry.centroid
            pt = ET.SubElement(pm, _e('Point'))
            ET.SubElement(pt, _e('coordinates')).text = f"{cen.x},{cen.y},0"

        print_detail(f"Layer 2: {len(merged)} analytics pins")

        # ── LAYER 3: 3BHK listings in Tier 1 wards only ────────
        layer3 = ET.SubElement(doc, _e('Folder'))
        ET.SubElement(layer3, _e('name')).text = "🏢 3BHK Acquisition Stock (Tier 1 Wards)"
        ET.SubElement(layer3, _e('visibility')).text = "0"

        tier1_wards = set(merged[merged['tier'] == 'Tier 1']['ward_id'].tolist())
        listings_3bhk = listings_gdf[
            (listings_gdf['bhk_type'] == 3) &
            (listings_gdf['ward_id'].isin(tier1_wards))
        ]

        for _, r in listings_3bhk.iterrows():
            pm = ET.SubElement(layer3, _e('Placemark'))
            ET.SubElement(pm, _e('name')).text = f"3BHK — {_fmt(r['monthly_rent'])}"
            ET.SubElement(pm, _e('styleUrl')).text = "#pin_3bhk"
            sqft = r['sqft'] if r.get('sqft', 0) > 0 else 1
            desc = (
                f"<div style='font-family:Segoe UI,sans-serif;'>"
                f"<b>3BHK Acquisition Target</b><br/>"
                f"<table border='1' cellpadding='4' style='border-collapse:collapse;font-size:12px;margin-top:8px;'>"
                f"<tr><td>Asking Rent</td><td><b>{_fmt(r['monthly_rent'])}/mo</b></td></tr>"
                f"<tr><td>Area</td><td>{r.get('sqft', 0):.0f} sqft</td></tr>"
                f"<tr><td>₹/sqft</td><td>{_fmt(r['monthly_rent']/sqft)}</td></tr>"
            )
            if 'listing_url' in r.index and pd.notna(r.get('listing_url')):
                desc += f"<tr><td>Link</td><td><a href='{r['listing_url']}'>View</a></td></tr>"
            desc += "</table></div>"
            ET.SubElement(pm, _e('description')).text = desc
            pt = ET.SubElement(pm, _e('Point'))
            ET.SubElement(pt, _e('coordinates')).text = f"{r.geometry.x},{r.geometry.y},0"

        print_detail(f"Layer 3: {len(listings_3bhk)} 3BHK listings in Tier 1 wards")

        # ── LAYER 4: Top 10 Star callouts ──────────────────────
        layer4 = ET.SubElement(doc, _e('Folder'))
        ET.SubElement(layer4, _e('name')).text = "🏆 Top 10 Priority Targets"
        ET.SubElement(layer4, _e('open')).text = "1"

        top10 = merged[merged['tier'] == 'Tier 1'].sort_values('OPP_SCORE', ascending=False).head(10)
        if len(top10) == 0:
            top10 = merged.sort_values('OPP_SCORE', ascending=False).head(10)

        for rank, (_, r) in enumerate(top10.iterrows(), 1):
            pm = ET.SubElement(layer4, _e('Placemark'))
            ET.SubElement(pm, _e('name')).text = f"#{rank}  {r.get('ward_name', '')}"
            ET.SubElement(pm, _e('styleUrl')).text = "#pin_top"
            ET.SubElement(pm, _e('description')).text = (
                f"<b>Rank #{rank}</b><br/>" + _ward_popup(r, tier_colors_html))
            cen = r.geometry.centroid
            pt = ET.SubElement(pm, _e('Point'))
            ET.SubElement(pt, _e('coordinates')).text = f"{cen.x},{cen.y},0"

        print_detail(f"Layer 4: {len(top10)} Top 10 callouts")

        path = os.path.join(config.OUTPUT_DIR, filename)
        os.makedirs(config.OUTPUT_DIR, exist_ok=True)
        _save_kml(kml, path)
        print_success(f"Investment Atlas KML → [highlight]{os.path.basename(path)}[/] (4 layers)")
        return path


# ═══════════════════════════════════════════════════════════════════
# CONSOLIDATED 4-SHEET EXCEL REPORT
# ═══════════════════════════════════════════════════════════════════
def export_lens_report_xlsx(df, stage_df, ols_model=None, morans_result=None,
                              filename='flent_lens_report.xlsx'):
    with log_process("Building Flent Lens Excel Report (4 sheets)"):
        try:
            from openpyxl import Workbook
            from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
            from openpyxl.formatting.rule import ColorScaleRule
            from openpyxl.utils import get_column_letter
            from openpyxl.chart import BarChart, Reference
        except ModuleNotFoundError:
            import subprocess, sys
            print_warning("openpyxl not found — auto-installing for this interpreter...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", "openpyxl", "--quiet"])
            from openpyxl import Workbook
            from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
            from openpyxl.formatting.rule import ColorScaleRule
            from openpyxl.utils import get_column_letter
            from openpyxl.chart import BarChart, Reference
        except Exception as import_err:
            import traceback
            print_warning(f"openpyxl import failed: {import_err}")
            traceback.print_exc()
            return None

        os.makedirs(config.OUTPUT_DIR, exist_ok=True)
        path = os.path.join(config.OUTPUT_DIR, filename)

        wb = Workbook()

        # ── Shared style primitives ──────────────────────────────
        def hdr(color='1F4E79'):
            return Font(name='Aptos', bold=True, color='FFFFFF', size=11), \
                   PatternFill('solid', fgColor=color)

        def fill(color):
            return PatternFill('solid', fgColor=color)

        def border():
            s = Side('thin', color='D5D5D5')
            return Border(left=s, right=s, top=s, bottom=s)

        thin = border()
        cell_font = Font(name='Aptos', size=10)
        tier_fills = {
            'Tier 1':   fill('C6EFCE'),
            'Tier 2':   fill('FFEB9C'),
            'Tier 3':   fill('FFCCCC'),
            'Excluded': fill('EEEEEE'),
        }

        # ── Qualitative Number Formats ──
        QUAL_FORMATS = {
            'Score': '[>=80]0.0" (Elite)";[>=60]0.0" (Strong)";0.0" (Mod/Weak)"',
            'Opp Score': '[>=80]0.0" (Elite)";[>=60]0.0" (Strong)";0.0" (Mod/Weak)"',
            'Final Score': '[>=80]0.0" (Elite)";[>=60]0.0" (Strong)";0.0" (Mod/Weak)"',
            'Base Score\n(Econ+DII+SFS)': '[>=80]0.0" (Elite)";[>=60]0.0" (Strong)";0.0" (Mod/Weak)"',
            'Score After Aura': '[>=80]0.0" (Elite)";[>=60]0.0" (Strong)";0.0" (Mod/Weak)"',
            'Transit Score': '[>=0.75]0.00" (High)";[>=0.40]0.00" (Good)";0.00" (Basic)"',
            'Transit': '[>=0.75]0.00" (High)";[>=0.40]0.00" (Good)";0.00" (Basic)"',
            'Demand Index': '[>=0.50]0.00" (High)";[>=0.30]0.00" (Mod)";0.00" (Low)"',
            'SEZ Score': '[>=0.70]0.00" (Core)";[>=0.30]0.00" (Conn)";0.00" (Peri)"',
            'Best Margin (₹)': '[>=25000]"₹"#,##0" (Elite)";[>=15000]"₹"#,##0" (Strong)";"₹"#,##0" (Mod)"',
            '3BHK Margin (₹)': '[>=25000]"₹"#,##0" (Elite)";[>=15000]"₹"#,##0" (Strong)";"₹"#,##0" (Mod)"',
            '1BHK Retail (₹)': '"₹"#,##0',
            '3BHK Monthly Acq (₹)': '"₹"#,##0',
            'Margin %': '0.0%',
            'Aura Mult.': '0.00"x"',
            'Aura Multiplier': '0.00"x"'
        }

        def write_header_row(ws, headers, bg='1F4E79', row=1):
            hf, hfill = hdr(bg)
            for ci, h in enumerate(headers, 1):
                c = ws.cell(row=row, column=ci, value=h)
                c.font = hf
                c.fill = hfill
                c.border = thin
                c.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)

        def write_data_row(ws, ri, values, headers, tier=None):
            for ci, val in enumerate(values, 1):
                val = _np_clean(val)
                c = ws.cell(row=ri, column=ci, value=val)
                c.font = cell_font
                c.border = thin
                c.alignment = Alignment(vertical='center')

                # Apply qualitative text formatting while retaining the raw numeric value
                h_name = headers[ci - 1] if ci - 1 < len(headers) else ''
                if h_name in QUAL_FORMATS and isinstance(val, (int, float)):
                    c.number_format = QUAL_FORMATS[h_name]
                elif h_name in ['1BHK Rent (₹)', '3BHK Acq Cost (₹)', '4BHK Acq Cost (₹)', 'Best Margin (₹)', '3BHK Margin (₹)'] and isinstance(val, (int, float)):
                    c.number_format = '"₹"#,##0'

                if tier and h_name == 'Tier' and tier in tier_fills:
                    c.fill = tier_fills[tier]
                    c.font = Font(name='Aptos', size=10, bold=True)
                elif tier and h_name == 'Investment Tier' and tier in tier_fills:
                    c.fill = tier_fills[tier]
                    c.font = Font(name='Aptos', size=10, bold=True)

        def autowidth(ws, max_col=None, sample_rows=20):
            max_col = max_col or ws.max_column
            for ci in range(1, max_col + 1):
                letter = get_column_letter(ci)
                mx = max(
                    len(str(ws.cell(row=r, column=ci).value or ''))
                    for r in range(1, min(sample_rows, ws.max_row) + 1)
                )
                ws.column_dimensions[letter].width = min(max(mx + 2, 10), 32)

        def colorscale(ws, col_letter, nrows):
            ws.conditional_formatting.add(
                f'{col_letter}2:{col_letter}{nrows}',
                ColorScaleRule(
                    start_type='min', start_color='F8696B',
                    mid_type='percentile', mid_value=50, mid_color='FFEB84',
                    end_type='max', end_color='63BE7B'))

        # ══════════════════════════════════════════════════════════
        # SHEET 1 — TOP 10 EXECUTIVE TARGETS
        # ══════════════════════════════════════════════════════════
        ws1 = wb.active
        ws1.title = "🏆 Top 10 Targets"
        ws1.sheet_properties.tabColor = '00B050'
        ws1.row_dimensions[1].height = 30

        top10_df = df[df['tier'] == 'Tier 1'].sort_values('OPP_SCORE', ascending=False).head(10)
        if len(top10_df) == 0:
            top10_df = df.sort_values('OPP_SCORE', ascending=False).head(10)

        top10_cols = ['ward_name', 'tier', 'OPP_SCORE', 'arb_margin_best',
                      'avg_rent_1bhk', 'avg_rent_3bhk',
                      'cnt_3bhk', 'cnt_4bhk', 'demand_intensity_idx']
        top10_labels = ['Rank', 'Ward', 'Tier', 'Score', 'Best Margin (₹)',
                        '1BHK Retail (₹)', '3BHK Monthly Acq (₹)',
                        '3BHK #', '4BHK #', 'Demand Index']

        if config.HAS_TRANSIT:
            top10_cols.append('transit_score')
            top10_labels.append('Transit')
        if config.HAS_SEZ:
            top10_cols.append('sez_employment_score')
            top10_labels.append('SEZ Score')
        top10_cols.append('aura_multiplier')
        top10_labels.append('Aura Mult.')

        write_header_row(ws1, top10_labels, bg='00B050', row=1)

        for rank, (_, row) in enumerate(top10_df.iterrows(), 1):
            ri = rank + 1
            # Prepend Rank to the data row
            vals = [rank] + [_np_clean(row.get(c, '')) for c in top10_cols]
            write_data_row(ws1, ri, vals, top10_labels, tier=row.get('tier'))

        ws1.freeze_panes = 'B2'
        ws1.row_dimensions[1].height = 28
        autowidth(ws1)

        # ══════════════════════════════════════════════════════════
        # SHEET 2 — FULL ANALYSIS (all wards)
        # ══════════════════════════════════════════════════════════
        ws2 = wb.create_sheet("📊 Full Analysis")
        ws2.sheet_properties.tabColor = '1F4E79'

        out = _pick(df, REPORT_COLUMNS).sort_values('OPP_SCORE', ascending=False)
        nums = out.select_dtypes(include=[np.number]).columns
        out[nums] = out[nums].round(2)

        headers2 = [COLUMN_LABELS.get(c, c) for c in out.columns]
        write_header_row(ws2, headers2)

        for ri, (_, row) in enumerate(out.iterrows(), 2):
            vals = [_np_clean(row[c]) for c in out.columns]
            write_data_row(ws2, ri, vals, headers2, tier=row.get('tier'))

        ws2.freeze_panes = 'A2'
        autowidth(ws2)

        # Color scale on OPP_SCORE
        if 'OPP_SCORE' in out.columns:
            ci = list(out.columns).index('OPP_SCORE') + 1
            colorscale(ws2, get_column_letter(ci), ws2.max_row)

        # ══════════════════════════════════════════════════════════
        # SHEET 3 — STAGE BREAKDOWN
        # ══════════════════════════════════════════════════════════
        ws3 = wb.create_sheet("📈 Stage Breakdown")
        ws3.sheet_properties.tabColor = '7030A0'

        stage_cols   = ['ward_name', 'score_base']
        stage_labels = ['Ward', 'Base Score\n(Econ+DII+SFS)']
        if config.HAS_TRANSIT:
            stage_cols.append('transit_score')
            stage_labels.append('Transit Score')
        if config.HAS_SEZ:
            stage_cols.append('sez_employment_score')
            stage_labels.append('SEZ Score')
        stage_cols   += ['aura_multiplier', 'score_after_aura', 'score_final', 'tier', 'arb_margin_best']
        stage_labels += ['Aura Multiplier', 'Score After Aura', 'Final Score', 'Tier', 'Best Margin (₹)']

        write_header_row(ws3, stage_labels, bg='7030A0')

        stage_out = stage_df.copy()
        # Sort by final score
        if 'score_final' in stage_out.columns:
            stage_out = stage_out.sort_values('score_final', ascending=False)

        for ri, (_, row) in enumerate(stage_out.iterrows(), 2):
            tier = row.get('tier', 'Excluded')
            vals = [_np_clean(row.get(c, '')) for c in stage_cols]
            write_data_row(ws3, ri, vals, stage_labels, tier=tier)

        ws3.freeze_panes = 'B2'
        ws3.row_dimensions[1].height = 40
        autowidth(ws3)

        # Progress bar color scale on score columns
        for col_name in ['score_base', 'score_after_aura', 'score_final']:
            if col_name in stage_cols:
                ci = stage_cols.index(col_name) + 1
                colorscale(ws3, get_column_letter(ci), ws3.max_row)

        # ══════════════════════════════════════════════════════════
        # SHEET 4 — OLS ARBITRAGE EVIDENCE
        # ══════════════════════════════════════════════════════════
        ws4 = wb.create_sheet("📐 OLS Evidence")
        ws4.sheet_properties.tabColor = 'FF6600'

        def label_val(ws, row, label, value, label_bg='FF6600'):
            lc = ws.cell(row=row, column=1, value=label)
            lc.font = Font(name='Aptos', bold=True, color='FFFFFF', size=11)
            lc.fill = fill(label_bg)
            lc.border = thin
            lc.alignment = Alignment(horizontal='right', vertical='center')
            vc = ws.cell(row=row, column=2, value=value)
            vc.font = Font(name='Aptos', size=11)
            vc.border = thin
            vc.alignment = Alignment(vertical='center')

        def section(ws, row, title, bg='333333'):
            lc = ws.cell(row=row, column=1, value=title)
            lc.font = Font(name='Aptos', bold=True, color='FFFFFF', size=12)
            lc.fill = fill(bg)
            lc.border = thin
            ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=3)

        row = 1
        ws4.column_dimensions['A'].width = 36
        ws4.column_dimensions['B'].width = 28
        ws4.column_dimensions['C'].width = 52

        section(ws4, row, "📐 Flent Lens — Arbitrage Structural OLS Results", 'FF6600')
        row += 1

        if ols_model is not None:
            beta      = float(ols_model.params.get('rent_1bhk', ols_model.params.iloc[1]))
            intercept = float(ols_model.params.iloc[0])
            r2        = float(ols_model.rsquared)
            nobs      = int(ols_model.nobs)
            pval      = float(ols_model.pvalues.iloc[1])
            breakeven = beta / 3.0
            ddf       = getattr(config, 'DEMAND_DISCOUNT_FACTOR', 0.80)
            proven    = ddf >= breakeven

            section(ws4, row, "Model Parameters", '1F4E79'); row += 1
            label_val(ws4, row, "Model", "OLS(Q25 3BHK Acq Cost ~ Median 1BHK Retail Rent)"); row += 1
            label_val(ws4, row, "Observations (Wards)", nobs); row += 1
            label_val(ws4, row, "R² (Fit Quality)", f"{r2:.4f}"); row += 1
            label_val(ws4, row, "Intercept (α)", f"₹{intercept:,.0f}"); row += 1
            label_val(ws4, row, "1BHK Cost Multiplier (β)", f"{beta:.3f}x"); row += 1
            label_val(ws4, row, "p-value (β)", f"{pval:.4f} {'✓ Significant' if pval < 0.05 else '✗ Not Significant at 5%'}"); row += 1

            row += 1
            section(ws4, row, "Arbitrage Proof", '1a7a34'); row += 1
            label_val(ws4, row, "Breakeven Demand Discount Min", f"{breakeven:.3f}  ({breakeven*100:.1f}%)"); row += 1
            label_val(ws4, row, "Flent's Operational DDF", f"{ddf:.2f}  ({ddf*100:.0f}%)"); row += 1
            label_val(ws4, row, "Arbitrage Thesis", "✅ STRUCTURALLY PROVEN" if proven else "⚠️ REVIEW REQUIRED"); row += 1

            row += 1
            section(ws4, row, "Plain-English Interpretation", '333333'); row += 1

            explanations = [
                ("What is β = {:.2f}?".format(beta),
                 "For every ₹1,000 increase in 1BHK market rent, the 3BHK acquisition cost "
                 "only rises by ₹{:,.0f}. Large assets are less price-elastic than rooms.".format(beta * 1000)),
                ("What is R² = {:.4f}?".format(r2),
                 "Only {:.1f}% of 3BHK price variation is explained by 1BHK pricing. "
                 "This is a feature, not a flaw — it confirms market fragmentation and "
                 "pricing inefficiency that Flent's model exploits.".format(r2 * 100)),
                ("Breakeven Discount = {:.1f}%".format(breakeven * 100),
                 "Flent needs to charge rooms at a minimum of {:.1f}% of a standalone 1BHK "
                 "rent to break even on the 3BHK master lease, assuming 3 rooms.".format(breakeven * 100)),
                ("Operational DDF = {:.0f}%".format(ddf * 100),
                 "Flent charges {:.0f}% of 1BHK rent per room — {:.1f} percentage points above "
                 "breakeven, proving positive structural arbitrage in this dataset.".format(
                     ddf * 100, (ddf - breakeven) * 100)),
            ]

            for label, explanation in explanations:
                lc = ws4.cell(row=row, column=1, value=label)
                lc.font = Font(name='Aptos', bold=True, size=10)
                lc.border = thin
                lc.alignment = Alignment(vertical='top', wrap_text=True)
                ec = ws4.cell(row=row, column=2, value=explanation)
                ec.font = Font(name='Aptos', size=10)
                ec.border = thin
                ec.alignment = Alignment(vertical='top', wrap_text=True, horizontal='left')
                ws4.merge_cells(start_row=row, start_column=2, end_row=row, end_column=3)
                ws4.row_dimensions[row].height = 52
                row += 1
        else:
            ws4.cell(row=row, column=1, value="OLS model not available — re-run pipeline.")
            row += 2

        # ── Moran's I Spatial Autocorrelation ──
        section(ws4, row, "🛰️ Moran's I Spatial Autocorrelation", '2e86de')
        row += 1
        if morans_result:
            mi = morans_result.get('moran_i', 0)
            pv = morans_result.get('p_value', 1.0)
            cl = "YES (Clustered)" if morans_result.get('clustered') else "NO (Random)"
            
            label_val(ws4, row, "Moran's I Index", mi, '2e86de'); row += 1
            label_val(ws4, row, "p-value", pv, '2e86de'); row += 1
            label_val(ws4, row, "Clustered?", cl, '2e86de'); row += 1
        else:
            ws4.cell(row=row, column=1, value="Moran's I result not available.")
            row += 1

        wb.save(path)
        print_success(f"Excel Report → [highlight]{os.path.basename(path)}[/] (4 sheets)")
        return path


# ═══════════════════════════════════════════════════════════════════
# GEOJSON (kept for future dashboard consumption)
# ═══════════════════════════════════════════════════════════════════
def export_geojson(df, wards_gdf, filename='ward_analysis.geojson'):
    with log_process("Exporting GeoJSON (dashboard data)"):
        os.makedirs(config.OUTPUT_DIR, exist_ok=True)
        path = os.path.join(config.OUTPUT_DIR, filename)
        gdf = wards_gdf.merge(df, on='ward_id')
        gdf.to_file(path, driver='GeoJSON')
        print_success(f"GeoJSON → [highlight]{os.path.basename(path)}[/] ({len(gdf)} features)")
        return path


# ═══════════════════════════════════════════════════════════════════
# 3BHK SUPPLY PRICE QUARTILE REPORT
# ═══════════════════════════════════════════════════════════════════
def export_3bhk_quartile_xlsx(quartile_df, ward_names_df,
                                filename='3bhk_supply_price_quartiles.xlsx'):
    """
    Export 3BHK supply price quartile breakdown to a formatted XLSX.
    Sheet 1: Quartile Summary (one row per ward)
    Sheet 2: Visual Reference (bar chart of top 20 wards)
    """
    with log_process("Building 3BHK Supply Price Quartile Report"):
        if quartile_df is None or len(quartile_df) == 0:
            print_warning("No quartile data — skipping 3BHK quartile export")
            return None

        try:
            from openpyxl import Workbook
            from openpyxl.styles import Font, PatternFill, Alignment, Border, Side, numbers
            from openpyxl.formatting.rule import ColorScaleRule
            from openpyxl.utils import get_column_letter
            from openpyxl.chart import BarChart, Reference
        except ModuleNotFoundError:
            import subprocess, sys
            print_warning("openpyxl not found — auto-installing...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", "openpyxl", "--quiet"])
            from openpyxl import Workbook
            from openpyxl.styles import Font, PatternFill, Alignment, Border, Side, numbers
            from openpyxl.formatting.rule import ColorScaleRule
            from openpyxl.utils import get_column_letter
            from openpyxl.chart import BarChart, Reference

        os.makedirs(config.OUTPUT_DIR, exist_ok=True)
        path = os.path.join(config.OUTPUT_DIR, filename)

        # Merge ward names
        out = quartile_df.merge(ward_names_df, on='ward_id', how='left')
        out['ward_name'] = out['ward_name'].fillna(out['ward_id'].astype(str))
        out = out.sort_values('total_3bhk_count', ascending=False).reset_index(drop=True)

        wb = Workbook()

        # ── Style primitives ──
        thin_side = Side('thin', color='D5D5D5')
        thin_border = Border(left=thin_side, right=thin_side, top=thin_side, bottom=thin_side)
        header_font = Font(name='Aptos', bold=True, color='FFFFFF', size=11)
        cell_font = Font(name='Aptos', size=10)
        cell_font_italic = Font(name='Aptos', size=10, italic=True, color='999999')
        currency_fmt = '"₹"#,##0'

        q1_fill = PatternFill('solid', fgColor='E8F5E9')   # light green  — budget
        q2_fill = PatternFill('solid', fgColor='FFF8E1')   # light amber  — moderate
        q3_fill = PatternFill('solid', fgColor='FFF3E0')   # light orange — above avg
        q4_fill = PatternFill('solid', fgColor='FFEBEE')   # light red    — premium

        # ══════════════════════════════════════════════════════════
        # SHEET 1 — QUARTILE SUMMARY
        # ══════════════════════════════════════════════════════════
        ws1 = wb.active
        ws1.title = "📊 Quartile Summary"
        ws1.sheet_properties.tabColor = '1565C0'

        headers = [
            'Ward Name', 'Total 3BHK',
            'Q1 Avg (₹)\nBottom 25%', 'Q1 #',
            'Q2 Avg (₹)\n25–50%', 'Q2 #',
            'Q3 Avg (₹)\n50–75%', 'Q3 #',
            'Q4 Avg (₹)\nTop 25%', 'Q4 #',
            'P25 (₹)', 'Median (₹)', 'P75 (₹)',
            'Spread (₹)\nQ4−Q1',
        ]
        data_cols = [
            'ward_name', 'total_3bhk_count',
            'q1_avg_rent', 'q1_count',
            'q2_avg_rent', 'q2_count',
            'q3_avg_rent', 'q3_count',
            'q4_avg_rent', 'q4_count',
            'p25', 'p50', 'p75',
            'spread',
        ]

        # Header row
        header_fill = PatternFill('solid', fgColor='1565C0')
        for ci, h in enumerate(headers, 1):
            c = ws1.cell(row=1, column=ci, value=h)
            c.font = header_font
            c.fill = header_fill
            c.border = thin_border
            c.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
        ws1.row_dimensions[1].height = 40

        # Quartile column fill mapping (1-indexed column → fill)
        quartile_fills = {3: q1_fill, 5: q2_fill, 7: q3_fill, 9: q4_fill}
        currency_cols = {3, 5, 7, 9, 11, 12, 13, 14}  # columns with ₹ values

        # Data rows
        for ri, (_, row) in enumerate(out.iterrows(), 2):
            is_insufficient = row.get('insufficient_data', False)

            for ci, col in enumerate(data_cols, 1):
                val = row.get(col, '')
                if isinstance(val, (np.integer,)):   val = int(val)
                if isinstance(val, (np.floating,)):  val = float(val)
                if isinstance(val, (np.bool_,)):     val = bool(val)

                # For insufficient data wards, show note in Q1 column
                if is_insufficient and ci == 3 and (pd.isna(val) or val == 0):
                    c = ws1.cell(row=ri, column=ci, value="< 4 listings")
                    c.font = cell_font_italic
                else:
                    c = ws1.cell(row=ri, column=ci, value=val if pd.notna(val) else '')

                    if ci in currency_cols and isinstance(val, (int, float)) and pd.notna(val):
                        c.number_format = currency_fmt
                    c.font = cell_font

                c.border = thin_border
                c.alignment = Alignment(vertical='center',
                                         horizontal='center' if ci >= 2 else 'left')

                # Apply quartile background fills
                if ci in quartile_fills:
                    c.fill = quartile_fills[ci]

        # Auto-width
        for ci in range(1, len(headers) + 1):
            letter = get_column_letter(ci)
            mx = max(
                len(str(ws1.cell(row=r, column=ci).value or ''))
                for r in range(1, min(25, ws1.max_row) + 1)
            )
            ws1.column_dimensions[letter].width = min(max(mx + 3, 12), 22)
        ws1.column_dimensions['A'].width = 28  # Ward name needs more room

        ws1.freeze_panes = 'B2'

        # Color scale on Spread column (col 14)
        if ws1.max_row > 1:
            ws1.conditional_formatting.add(
                f'N2:N{ws1.max_row}',
                ColorScaleRule(
                    start_type='min', start_color='63BE7B',
                    mid_type='percentile', mid_value=50, mid_color='FFEB84',
                    end_type='max', end_color='F8696B'))

        total_wards = len(out)
        print_detail(f"Sheet 1: {total_wards} wards in quartile summary")

        # ══════════════════════════════════════════════════════════
        # SHEET 2 — VISUAL REFERENCE (Bar Chart)
        # ══════════════════════════════════════════════════════════
        ws2 = wb.create_sheet("📈 Visual Reference")
        ws2.sheet_properties.tabColor = '00B050'

        # Take top 20 wards by listing count for chart readability
        chart_data = out[out['insufficient_data'] == False].head(20).copy()

        if len(chart_data) > 0:
            # Write mini data table for chart source
            chart_headers = ['Ward', 'Q1 Avg (₹)', 'Q2 Avg (₹)', 'Q3 Avg (₹)', 'Q4 Avg (₹)']
            chart_fill = PatternFill('solid', fgColor='00B050')
            for ci, h in enumerate(chart_headers, 1):
                c = ws2.cell(row=1, column=ci, value=h)
                c.font = header_font
                c.fill = chart_fill
                c.border = thin_border
                c.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)

            for ri, (_, row) in enumerate(chart_data.iterrows(), 2):
                ws2.cell(row=ri, column=1, value=row['ward_name']).font = cell_font
                for ci, col in enumerate(['q1_avg_rent', 'q2_avg_rent', 'q3_avg_rent', 'q4_avg_rent'], 2):
                    val = row.get(col, 0)
                    if isinstance(val, (np.integer,)):   val = int(val)
                    if isinstance(val, (np.floating,)):  val = float(val)
                    c = ws2.cell(row=ri, column=ci, value=val if pd.notna(val) else 0)
                    c.number_format = currency_fmt
                    c.font = cell_font
                    c.border = thin_border

            ws2.column_dimensions['A'].width = 28

            # Create grouped bar chart
            chart = BarChart()
            chart.type = "col"
            chart.grouping = "clustered"
            chart.title = "3BHK Supply Price — Quartile Averages by Ward (Top 20)"
            chart.y_axis.title = "Monthly Rent (₹)"
            chart.x_axis.title = "Ward"
            chart.style = 10
            chart.width = 38
            chart.height = 18

            nrows = len(chart_data) + 1
            data_ref = Reference(ws2, min_col=2, min_row=1, max_col=5, max_row=nrows)
            cats_ref = Reference(ws2, min_col=1, min_row=2, max_row=nrows)
            chart.add_data(data_ref, titles_from_data=True)
            chart.set_categories(cats_ref)

            # Color the series
            colors = ['7CB342', 'FFA726', 'EF5350', 'AB47BC']  # green, orange, red, purple
            for i, color in enumerate(colors):
                if i < len(chart.series):
                    chart.series[i].graphicalProperties.solidFill = color

            chart.shape = 4
            ws2.add_chart(chart, "A" + str(nrows + 3))

            print_detail(f"Sheet 2: bar chart for top {len(chart_data)} wards")
        else:
            ws2.cell(row=1, column=1, value="Insufficient data for chart").font = Font(
                name='Aptos', size=12, italic=True, color='999999')

        wb.save(path)
        print_success(f"3BHK Quartile Report → [highlight]{os.path.basename(path)}[/] (2 sheets, {total_wards} wards)")
        return path
