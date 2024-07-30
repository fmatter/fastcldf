from fastcldf import create_cldf

def test_create(tmpdir):
    ds = create_cldf(
        tables={
            "languages": [{"id": "lg-1", "name": "Ikpeng"}],
            "forms": [
                {
                    "id": "form-1",
                    "form": "yay",
                    "parameter": "tree",
                    "language": "lg-1",
                    "arbitrary": "content",
                }
            ],
            "wordforms": [
                {"id": "wf-1", "form": "yay", "parameter": "tree", "language": "lg-1"}
            ],
        },
        spec={
            "dir": tmpdir,
            "module": "Generic",
            "metadata_fname": "cldf-metadata.json",
        },
    )
    ds.validate()
