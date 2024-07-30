import pandas as pd
from cldfbench import CLDFSpec
from cldfbench.cldf import CLDFWriter
from loguru import logger as log
from pycldf.dataset import MD_SUFFIX
from pycldf.util import pkg_path
from writio import dump, load


def find_column_name(col, target_cols):
    targets = [col, col.capitalize(), col.upper()]
    for target_col, data in target_cols.items():
        handle = data.get("propertyUrl", "").split("#")[1]
        for target in targets:
            if target in target_cols:
                return target_cols[target]
            elif target == handle or target == handle.replace("Reference", ""):
                return data
    return None


def create_cldf(
    tables,
    metadata={},
    spec={
        "dir": "./cldf",
        "module": "Generic",
        "metadata_fname": "metadata.json",
    },  # empty cldf specification (https://github.com/cldf/cldf/blob/master/modules/Generic/Generic-metadata.json)
):
    """Creates a CLDF dataset.

    Parameters
    ----------
    tables : dict
      A dict linking table names ("languages" etc.) to lists of records ([{"id": "lg-1", "name": "Language 1"} etc.]).
    metadata: dict
      A dict containing metadata about the dataset.
    spec : dict
      A dict representing a [cldfbench](https://github.com/cldf/cldfbench) spec
    Returns
    -------
    pycldf.dataset
        A [pycldf dataset](https://pycldf.readthedocs.io/en/latest/dataset.html)
    """
    with CLDFWriter(CLDFSpec(**spec)) as writer:
        # mapping e.g. "examples.csv" to e.g. "ExampleTable", to use add_component("ExampleTable") later
        components = {}
        cldf_data = {}
        for component_filename in pkg_path(
            "components"
        ).iterdir():  # .../.../pycldf/components/Example-Metadata.json
            component = load(component_filename)
            handle = component["url"].replace(".csv", "")
            cldf_data[handle] = load(component_filename)  # {"url": "examples.csv", ...}
            components[handle] = str(component_filename.name).replace(
                MD_SUFFIX, ""
            )  # "examples": Example
        column_data = {"general": {}}
        for table in components:
            column_data[table] = {}
            for column in cldf_data[table]["tableSchema"]["columns"]:
                column_data[table][column["name"]] = column
                column_data["general"][column["name"]] = column
        for table, data in tables.items():
            df = pd.DataFrame.from_dict(data).fillna("")
            added_cols = {}
            if table in components:
                for col in df.columns:
                    coldata = find_column_name(
                        col, column_data[table]
                    ) or find_column_name(col, column_data["general"])
                    if coldata:
                        df = df.rename(columns={col: coldata["name"]})
                    else:
                        added_cols[col] = col

                url = components[table]
                writer.cldf.add_component(components[table])
                for col, coldata in added_cols.items():
                    log.info(f"Adding unspecified column: {col}")
                    writer.cldf.add_columns(components[table], coldata)
            else:
                for col in df.columns:
                    coldata = find_column_name(col, column_data["general"])
                    if coldata:
                        df = df.rename(columns={col: coldata["name"]})
                        added_cols[col] = coldata
                    else:
                        added_cols[col] = {"name": col.capitalize()}

                url = f"{table}.csv"
                cpt_data = {"url": url, "tableSchema": {"columns": []}}
                writer.cldf.add_component(cpt_data)
                for col, coldata in added_cols.items():
                    log.info(f"Adding unspecified column: {coldata['name']}")
                    writer.cldf.add_columns(url, coldata)
                    df = df.rename(columns={col: coldata["name"]})

            for rec in df.to_dict("records")[0:1]:
                writer.objects[url].append(rec)
        writer.cldf.write()
        ds = writer.cldf
    return ds

    #     # mapping columns to required table transformation workflows
    #     table_actions = {
    #         "Source": lambda x: splitcol(x, "Source"),
    #         "Gloss": lambda x: splitcol(x, "Gloss", sep=" "),
    #         "Analyzed_Word": lambda x: splitcol(x, "Analyzed_Word", sep=" "),
    #         # "Parameter_ID": lambda x: parse_param(x),
    #         "Segments": lambda x: splitcol(x, "Segments", sep=" "),
    #         "Alignment": lambda x: splitcol(x, "Alignment", sep=" "),
    #     }
