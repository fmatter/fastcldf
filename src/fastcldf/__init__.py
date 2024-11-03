"""Main fastcldf module"""
from pathlib import Path

import pandas as pd
import pybtex
from cldfbench import CLDFSpec
from cldfbench.cldf import CLDFWriter
from loguru import logger as log
from pycldf import Dataset
from pycldf.dataset import MD_SUFFIX
from pycldf.sources import Source
from pycldf.util import pkg_path
from writio import load


def find_column_name(col, target_cols):
    targets = [col, col.capitalize(), col.upper()]
    for data in target_cols.values():
        handle = data.get("propertyUrl", "").split("#")[1]
        for target in targets:
            if target in target_cols:
                return target_cols[target]
            if target == handle or target == handle.replace("Reference", ""):
                return data
    return None


def load_cldf_data():
    component_names = {}
    component_data = {}
    for component_filename in pkg_path(
        "components"
    ).iterdir():  # .../.../pycldf/component_names/Example-Metadata.json
        component = load(component_filename)
        handle = component["url"].replace(".csv", "")
        component_data[handle] = load(
            component_filename
        )  # {"url": "examples.csv", ...}
        component_names[handle] = str(component_filename.name).replace(
            MD_SUFFIX, ""
        )  # "examples": Example
    cldf_col_data = {"general": {}}
    for table in component_names:
        cldf_col_data[table] = {}
        for column in component_data[table]["tableSchema"]["columns"]:
            cldf_col_data[table][column["name"]] = column
            cldf_col_data["general"][column["name"]] = column
    return component_names, component_data, cldf_col_data


def process_native_table(
    table, df, component_names, cldf_col_data, writer, user_columns, foreignkeys
):
    added_cols = {}
    for col in df.columns:
        coldata = find_column_name(col, cldf_col_data[table])
        if not coldata:
            coldata = find_column_name(col, cldf_col_data["general"])
            if coldata:
                added_cols[coldata["name"]] = coldata
        if coldata:
            df = df.rename(columns={col: coldata["name"]})
        elif col in user_columns:
            df = df.rename(
                columns={col: user_columns[col].get("name", col.capitalize())}
            )
        else:
            added_cols[col] = {"name": col.capitalize()}
    writer.cldf.add_component(component_names[table])
    for col, coldata in added_cols.items():
        log.info(f"Adding unspecified column: {col}")
        writer.cldf.add_columns(component_names[table], coldata)
    for colname, cdata in user_columns.items():
        if colname in cldf_col_data[table]:
            writer.cldf.remove_columns(component_names[table], colname)
        writer.cldf.add_columns(component_names[table], cdata)
    for colname, ref in foreignkeys.items():
        writer.cldf.add_foreign_key(component_names[table], colname, ref, "ID")
    return component_names[table], df


def process_nonnative_table(
    table, df, cldf_col_data, writer, user_columns, foreignkeys
):
    added_cols = {}
    for col in df.columns:
        coldata = find_column_name(col, cldf_col_data["general"])
        if coldata:
            df = df.rename(columns={col: coldata["name"]})
            added_cols[col] = coldata
        else:
            added_cols[col] = {"name": col.capitalize()}
    url = f"{table}.csv"
    if url not in [
        str(tbl.url) for tbl in writer.cldf.tables
    ]:  # already present table?
        writer.cldf.add_component({"url": url, "tableSchema": {"columns": []}})
        for col, coldata in added_cols.items():
            log.info(f"Adding unspecified column: {coldata['name']}")
            writer.cldf.add_columns(url, coldata)
            df = df.rename(columns={col: coldata["name"]})
    return url, df


def create_cldf(
    tables,
    sources,
    spec=None,
    metadata=None,
    columns=None,
    foreignkeys=None,
    cldf_tables=None,
    validate=True,
):
    """Creates a CLDF dataset.

    Parameters
    ----------
    tables : dict
      A dict linking table names ("languages" etc.) to
      lists of records ([{"id": "lg-1", "name": "Language 1"} etc.]).
    sources : str
      A path to a .bib file
    metadata: dict
      A dict containing metadata about the dataset.
    spec : dict
      A dict representing a [cldfbench](https://github.com/cldf/cldfbench) spec
    Returns
    -------
    pycldf.dataset
        A pycldf dataset, see
        [here](https://pycldf.readthedocs.io/en/latest/dataset.html)
        for details
    """
    metadata = metadata or {}
    spec = spec or {
        "dir": "./cldf",
        "module": "Generic",
        "metadata_fname": "metadata.json",
    }
    columns = columns or {}
    foreignkeys = foreignkeys or {}
    cldf_tables = cldf_tables or []
    with CLDFWriter(CLDFSpec(**spec)) as writer:
        for component in cldf_tables:
            writer.cldf.add_component(component)
        component_names, component_data, cldf_col_data = load_cldf_data()
        for table, data in tables.items():
            df = pd.DataFrame.from_dict(data).fillna("")
            if table in component_names:
                url, df = process_native_table(
                    table,
                    df,
                    component_names,
                    cldf_col_data,
                    writer,
                    user_columns=columns.get(table, {}),
                    foreignkeys=foreignkeys.get(table, {}),
                )
            else:
                url, df = process_nonnative_table(
                    table,
                    df,
                    cldf_col_data,
                    writer,
                    user_columns=columns.get(table, {}),
                    foreignkeys=foreignkeys.get(table, {}),
                )
            for rec in df.to_dict("records"):
                writer.objects[url].append(rec)

        source_path = Path(sources)
        sources = None
        if source_path.is_file():
            sources = pybtex.database.parse_file(source_path)
            writer.cldf.add_sources(
                *[Source.from_entry(k, e) for k, e in sources.entries.items()]
            )
        writer.cldf.write()
        ds = writer.cldf
    if validate:
        ds.validate()
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


def load_cldf(metadata_file):
    """Load data from a CLDF dataset

        Parameters
        -----------
        metadata_file : str
            A path to a `.json` metadata file.

        Returns
        -------
        data : dict
            A dict where
    * e.g. `"examples.csv"` contains the example table records (list)
    * `"metadata"` contains the metadata (dict)
    * `"sources"` contains the bibfile (str)
    """
    ds = Dataset.from_metadata(metadata_file)
    data = {}
    for table in ds.tables:
        res = []
        for rec in ds.iter_rows(table.url):
            res.append(rec)
        data[str(table.url)] = res
    data["metadata"] = ds.metadata_dict
    data["sources"] = load(ds.bibpath)
    return data
