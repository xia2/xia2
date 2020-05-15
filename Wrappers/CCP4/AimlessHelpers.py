import xml.dom.minidom


def parse_aimless_xml(xml_file):
    aimless_xml_names_to_standard = {
        "AnomalousCompleteness": "Anomalous completeness",
        "AnomalousMultiplicity": "Anomalous multiplicity",
        "Completeness": "Completeness",
        "AnomalousCChalf": "Anomalous correlation",
        "ResolutionHigh": "High resolution limit",
        "ResolutionLow": "Low resolution limit",
        "MeanIoverSD": "I/sigma",
        "AnomalousNPslope": "Anomalous slope",
        "Multiplicity": "Multiplicity",
        "RmergeOverall": "Rmerge(I)",
        "Rmerge": "Rmerge(I+/-)",
        "RmeasOverall": "Rmeas(I)",
        "Rmeas": "Rmeas(I+/-)",
        "RpimOverall": "Rpim(I)",
        "Rpim": "Rpim(I+/-)",
        "NumberObservations": "Total observations",
        "NumberReflections": "Total unique",
        "CChalf": "CC half",
    }

    total_summary = {}

    dom = xml.dom.minidom.parse(xml_file)
    result = dom.getElementsByTagName("Result")[0]

    datasets = result.getElementsByTagName("Dataset")
    for j, dataset in enumerate(datasets):
        summary = {}
        pname, xname, dname = list(map(str, dataset.getAttribute("name").split("/")))

        for xml_name, standard in aimless_xml_names_to_standard.items():
            row = result.getElementsByTagName(xml_name)[j]
            if len(row.childNodes) == 3:
                summary[standard] = tuple(
                    float(row.getElementsByTagName(item)[0].childNodes[0].data.strip())
                    for item in ("Overall", "Inner", "Outer")
                )
            elif len(row.childNodes) == 1:
                summary[standard] = (float(row.childNodes[0].data.strip()), 0.0, 0.0)

        total_summary[(pname, xname, dname)] = summary

    return total_summary
