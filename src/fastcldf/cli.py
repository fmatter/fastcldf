"""The fastcldf command line interface"""
import sys
from pathlib import Path

import click
from writio import load

from fastcldf import create_cldf, log


@click.command()
@click.argument("data_dir", type=click.Path(exists=True))
@click.option("-s", "--spec", type=click.Path(exists=True))
@click.option("-m", "--metadata", type=click.Path(exists=True))
def main(data_dir, spec, metadata):
    """Creates a CLDF dataset.

    Parameters
    ----------
    data_dir : click.Path
      A directory containing the data you want to transform to a CLDF dataset
    metadata : click.Path
      A .yaml or .json file containing metadata for the dataset
    spec : click.Path
      A .yaml or .json file containing the desired CLDFSpec values"""
    data_dir = Path(data_dir)
    tables = {}
    kwargs = {}
    if metadata:
        kwargs["metadata"] = load(metadata)
    if spec:
        kwargs["spec"] = load(spec)
    for file in data_dir.iterdir():
        if file.suffix in [".csv", ".tsv"]:
            tables[file.stem] = load(file).to_dict("records")
        elif file.suffix in [".json", ".yaml"]:
            if file.stem in ["metadata", "spec"]:
                if file.stem not in kwargs:
                    kwargs[file.stem] = load(file)
                else:
                    log.warning(
                        f"Ignoring file {file}, since "
                        f"argument {file.stem} is already defined"
                    )
            else:
                tables[file.stem] = load(file)
    dataset = create_cldf(tables=tables, **kwargs)
    dataset.validate()


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1::]))  # pragma: no cover
