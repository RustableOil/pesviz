"""Read pARTn search file and validate input"""

import pandas

#TODO: implement HDF5 file reading; only add once pyKMC supports HDF5 file writeout

def import_partn_search(filepath):
    """Load a pARTn search dataframe from a pandas pickle at filepath."""
    if filepath is not None:
        df = pandas.read_pickle(filepath)
        return df
    else:
        raise TypeError("No valid search file path provided.")
