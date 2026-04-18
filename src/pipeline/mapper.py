import csv
import math
import os
import config
import xml.etree.ElementTree as ET
from src.utils.logger import console, print_success, print_error, print_info, log_process

ENRICHMENTS = {
    "Manyata Promoters Pvt. Ltd.": {"Acres": "330 total (110-122 SEZ)", "Employees": "~100k-200k", "Notes": "Extensive IT/ITES integrated township"},
    "Global Village Techparks Pvt. Ltd.": {"Acres": "78.3", "Employees": "Large scale IT hub", "Notes": "12.1 million sqft. built-up"},
    "Arliga Ecoworld Infrastructure": {"Acres": "80+", "Employees": "~65,000", "Notes": "RMZ Ecoworld, major ORR tech park"},
    "Cessna Business Park Pvt. Ltd.": {"Acres": "~22", "Employees": "~40,000", "Notes": "Hosts Cisco, HCL, Accenture, etc."},
    "Information Technology Park Limited": {"Acres": "69", "Employees": "~55,000+", "Notes": "ITPB / Whitefield pioneer SEZ"},
    "Wipro Limited": {"Acres": "Varies", "Employees": "Major cluster", "Notes": "Multiple massive ORR/ECity parks"},
    "Infosys": {"Acres": "80+", "Employees": "Massive hub", "Notes": "Electronic City powerhouse"}
}

def generate_circle_coordinates(lat, lon, radius_m=179.45, num_points=36):
    coords = []
    lat_r = math.radians(lat)
    lon_r = math.radians(lon)
    R = 6378137.0
    for i in range(num_points + 1):
        theta = 2.0 * math.pi * (i / num_points)
        dx = radius_m * math.cos(theta)
        dy = radius_m * math.sin(theta)
        d_lat = dy / R
        d_lon = dx / (R * math.cos(lat_r))
        point_lat = lat + math.degrees(d_lat)
        point_lon = lon + math.degrees(d_lon)
        coords.append(f"{point_lon},{point_lat},0")
    return " ".join(coords)

def build_description(dev, type_, location):
    html = f"<h3>SEZ: {dev}</h3>"
    html += "<table border='1' cellpadding='4' style='border-collapse: collapse; width: 100%; font-family: sans-serif; font-size: 13px;'>"
    html += "<tr style='background-color: #f2f2f2;'><th style='text-align: left;'>Type</th><th style='text-align: left;'>Location</th><th style='text-align: left;'>Enriched Metrics</th></tr>"
    info = "No specific gathered data"
    for key, val in ENRICHMENTS.items():
        if key.lower() in dev.lower():
            info = f"<b>{val.get('Acres', 'N/A')} Acres</b> <br> {val.get('Employees', 'N/A')} <br> <i>{val.get('Notes', '')}</i>"
            break
    html += f"<tr><td>{type_}</td><td>{location}</td><td>{info}</td></tr>"
    html += "</table>"
    return html

def generate_sez_kml(input_path=config.SEZ_CSV, output_path=config.SEZ_KML):
    with log_process("SEZ Geometry Generation"):
        if not os.path.exists(input_path):
            print_error(f"Geocoded SEZ table not found at {input_path}")
            return

        kml_ns = "http://www.opengis.net/kml/2.2"
        ET.register_namespace('', kml_ns)
        kml = ET.Element('{http://www.opengis.net/kml/2.2}kml')
        doc = ET.SubElement(kml, '{http://www.opengis.net/kml/2.2}Document')
        name_elem = ET.SubElement(doc, '{http://www.opengis.net/kml/2.2}name')
        name_elem.text = "Mathematical 25-Acre SEZ Overlay"

        styles = [
            '<Style xmlns="http://www.opengis.net/kml/2.2" id="StyleIT"><LineStyle><color>ffc00000</color><width>2</width></LineStyle><PolyStyle><color>B2ff0000</color></PolyStyle></Style>',
            '<Style xmlns="http://www.opengis.net/kml/2.2" id="StyleAero"><LineStyle><color>ff0000c0</color><width>2</width></LineStyle><PolyStyle><color>B20000ff</color></PolyStyle></Style>',
            '<Style xmlns="http://www.opengis.net/kml/2.2" id="StyleBio"><LineStyle><color>ff00c000</color><width>2</width></LineStyle><PolyStyle><color>B200ff00</color></PolyStyle></Style>'
        ]
        for s in styles:
            doc.append(ET.fromstring(s))

        folder = ET.SubElement(doc, '{http://www.opengis.net/kml/2.2}Folder')
        ET.SubElement(folder, '{http://www.opengis.net/kml/2.2}name').text = "Spatial Points"

        count = 0
        with open(input_path, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                lat = row.get('latitude', '').strip()
                lon = row.get('longitude', '').strip()
                if not lat or not lon: continue
                
                lat, lon = float(lat), float(lon)
                dev = row.get('developer', 'Unknown')
                type_str = row.get('type', 'IT')
                loc = row.get('location', '')
                
                style_id = "StyleIT"
                if 'AEROSPACE' in type_str.upper(): style_id = "StyleAero"
                elif 'BIO' in type_str.upper(): style_id = "StyleBio"
                
                pm = ET.SubElement(folder, '{http://www.opengis.net/kml/2.2}Placemark')
                ET.SubElement(pm, '{http://www.opengis.net/kml/2.2}name').text = dev[:40] + "..."
                ET.SubElement(pm, '{http://www.opengis.net/kml/2.2}description').text = build_description(dev, type_str, loc)
                ET.SubElement(pm, '{http://www.opengis.net/kml/2.2}styleUrl').text = f"#{style_id}"
                
                poly = ET.SubElement(pm, '{http://www.opengis.net/kml/2.2}Polygon')
                inner = ET.SubElement(poly, '{http://www.opengis.net/kml/2.2}outerBoundaryIs')
                lr = ET.SubElement(inner, '{http://www.opengis.net/kml/2.2}LinearRing')
                ET.SubElement(lr, '{http://www.opengis.net/kml/2.2}coordinates').text = generate_circle_coordinates(lat, lon, 179.45)
                count += 1

        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        tree = ET.ElementTree(kml)
        tree.write(output_path, xml_declaration=True, encoding='utf-8')
        print_success(f"Generated [highlight]{count}[/highlight] circular geometries -> [highlight]{os.path.basename(output_path)}[/highlight]")

if __name__ == "__main__":
    generate_sez_kml()
