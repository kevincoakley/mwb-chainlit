from io import StringIO
from typing import Any, Optional

import pandas as pd
import requests
import json

BASE_URL = "https://www.metabolomicsworkbench.org/rest"


def get_study_summary(study_id: str = "ST") -> dict[str, Any]:
    """Fetch summary information for a study.

    Args:
        study_id (str): The study ID to fetch (e.g., 'ST000001').
            Defaults to 'ST' which retrieves all studies.

    Returns:
        dict: A dictionary containing the study summary or an error message.
    """
    return _get(f"study/study_id/{study_id}/summary")


def get_study_analysis_information(study_id: str = "ST") -> dict[str, Any]:
    """Fetch analysis information for a study.

    Args:
        study_id (str): The study ID to fetch (e.g., 'ST000001').
            Defaults to 'ST' which retrieves all studies.

    Returns:
        dict: A dictionary containing the study analysis information or an error message.
    """
    return _get(f"study/study_id/{study_id}/analysis")


def get_analysis_datatable(analysis_id: str = "AN") -> pd.DataFrame:
    """Fetch analysis datatable for an analysis ID and return it as a DataFrame.

    Args:
        analysis_id (str): The analysis ID to fetch (e.g., 'AN000001').
            Defaults to 'AN' which retrieves all analyses.

    Returns:
        pd.DataFrame: A DataFrame containing the analysis datatable response.
    """
    url = f"{BASE_URL}/study/analysis_id/{analysis_id}/datatable"

    try:
        response = requests.get(url)
        response.raise_for_status()
        return pd.read_csv(StringIO(response.text), sep="\t")
    except requests.exceptions.RequestException as exc:
        return pd.DataFrame([{"error": f"API request failed: {str(exc)}"}])
    except pd.errors.EmptyDataError:
        return pd.DataFrame([{"error": "No tabular data returned"}])


def get_study_factors(study_id: str) -> dict[str, Any]:
    """Fetch samples and experimental variables (factors) for a study.

    Args:
        study_id (str): The study ID to fetch.

    Returns:
        dict: A dictionary containing the study factors or an error message.
    """
    return _get(f"study/study_id/{study_id}/factors")


def get_study_metabolites(study_id: str) -> dict[str, Any]:
    """Fetch metabolites and annotations detected in a study.

    Args:
        study_id (str): The study ID to fetch.

    Returns:
        dict: A dictionary containing the study metabolites or an error message.
    """
    return _get(f"study/study_id/{study_id}/metabolites")


def get_study_data(study_id: str) -> dict[str, Any]:
    """Fetch metabolites measurements for a study.

    Args:
        study_id (str): The study ID to fetch.

    Returns:
        dict: A dictionary containing the study data or an error message.
    """
    return _get(f"study/study_id/{study_id}/data")


def get_study_mwtab(analysis_id: str) -> dict[str, Any]:
    """Fetch mwTab content for an analysis within a study.

    Args:
        analysis_id (str): The analysis ID to fetch.

    Returns:
        dict: A dictionary containing the mwTab content or an error message.
    """
    return _get(f"study/analysis_id/{analysis_id}/mwtab")


def get_untargeted_studies() -> dict[str, Any]:
    """Fetch list of studies with untargeted data in NMDR.

    Returns:
        dict: A dictionary containing the list of untargeted studies or an error message.
    """
    return _get("study/study_id/x/untarg_studies")


def get_untargeted_data(analysis_id: str) -> dict[str, Any]:
    """Fetch untargeted data for an analysis within a study.

    Args:
        analysis_id (str): The analysis ID to fetch.

    Returns:
        dict: A dictionary containing the untargeted data or an error message.
    """
    return _get(f"study/analysis_id/{analysis_id}/untarg_data")


def get_untargeted_factors(analysis_id: str) -> dict[str, Any]:
    """Fetch experimental factors for an untargeted data analysis.

    Args:
        analysis_id (str): The analysis ID to fetch.

    Returns:
        dict: A dictionary containing the untargeted factors or an error message.
    """
    return _get(f"study/analysis_id/{analysis_id}/untarg_factors")


def get_named_metabolite_studies() -> dict[str, Any]:
    """Fetch list of studies with named metabolites in NMDR.

    Returns:
        dict: A dictionary containing the list of named metabolite studies or an error message.
    """
    return _get("study/study_id/ST/named_metabolites")


def get_number_of_metabolites(study_id: str) -> dict[str, Any]:
    """Show number of named metabolites in a study.

    Args:
        study_id (str): The study ID to fetch.

    Returns:
        dict: A dictionary containing the metabolite count or an error message.
    """
    return _get(f"study/study_id/{study_id}/number_of_metabolites")


def get_metabolite_id_info(metabolite_id: str) -> dict[str, Any]:
    """Show metabolite name and RefMet name for a metabolite_id.

    Args:
        metabolite_id (str): The metabolite ID to fetch.

    Returns:
        dict: A dictionary containing the metabolite info or an error message.
    """
    return _get(f"study/metabolite_id/{metabolite_id}/available")


def get_compound_info(
    input_item: str, input_value: str, output_item: str = "all"
) -> dict[str, Any]:
    """Fetch compound information.

    Args:
        input_item (str): The input item type (e.g., 'regno', 'pubchem_cid', 'inchi_key',
            'formula', 'lm_id', 'hmdb_id', 'kegg_id').
        input_value (str): The value for the input item.
        output_item (str): The output item type (e.g., 'all', 'classification', 'name',
            'sys_name', 'smiles'). Defaults to 'all'.

    Returns:
        dict: A dictionary containing the compound information or an error message.
    """
    return _get(f"compound/{input_item}/{input_value}/{output_item}")


def get_refmet_info(
    input_item: str, input_value: Optional[str] = None, output_item: str = "all"
) -> dict[str, Any]:
    """Fetch RefMet information.

    Args:
        input_item (str): The input item type (e.g., 'name', 'inchi_key', 'pubchem_cid',
            'exactmass', 'formula', 'all', 'all_ids', 'classification').
        input_value (Optional[str]): The value for the input item. Defaults to None.
        output_item (str): The output item type. Defaults to 'all'.

    Returns:
        dict: A dictionary containing the RefMet information or an error message.
    """
    if input_value:
        return _get(f"refmet/{input_item}/{input_value}/{output_item}")
    return _get(f"refmet/{input_item}")


def get_metstat(
    analysis_type: str = "",
    polarity: str = "",
    chromatography: str = "",
    species: str = "",
    sample_source: str = "",
    disease: str = "",
    kegg_id: str = "",
    refmet_name: str = "",
) -> dict[str, Any]:
    """Fetch studies based on MetStat criteria.

    The criteria follow the format:
    /rest/metstat/<ANALYSIS_TYPE>;<POLARITY>;<CHROMATOGRAPHY>;<SPECIES>;<SAMPLE SOURCE>;<DISEASE>;<KEGG_ID>;<REFMET_NAME>

    Args:
        analysis_type (str): Type of analysis.
        polarity (str): Ion polarity.
        chromatography (str): Type of chromatography.
        species (str): Biological species.
        sample_source (str): Sample source/tissue.
        disease (str): Disease association.
        kegg_id (str): KEGG identifier.
        refmet_name (str): RefMet name.

    Returns:
        dict: A dictionary containing the matching studies or an error message.
    """
    parts = [
        analysis_type,
        polarity,
        chromatography,
        species,
        sample_source,
        disease,
        kegg_id,
        refmet_name,
    ]
    endpoint = f"metstat/{';'.join(parts)}"
    return _get(endpoint)


def get_gene_info(
    input_item: str, input_value: str, output_item: str = "all"
) -> dict[str, Any]:
    """Fetch gene fields.

    Args:
        input_item (str): The input item type.
        input_value (str): The value for the input item.
        output_item (str): The output item type. Defaults to 'all'.

    Returns:
        dict: A dictionary containing the gene fields or an error message.
    """
    return _get(f"gene/{input_item}/{input_value}/{output_item}")


def get_protein_info(
    input_item: str, input_value: str, output_item: str = "all"
) -> dict[str, Any]:
    """Fetch protein fields.

    Args:
        input_item (str): The input item type.
        input_value (str): The value for the input item.
        output_item (str): The output item type. Defaults to 'all'.

    Returns:
        dict: A dictionary containing the protein fields or an error message.
    """
    return _get(f"protein/{input_item}/{input_value}/{output_item}")


def search_moverz(
    context: str, mz: float, adduct: str, tolerance: float
) -> dict[str, Any]:
    """Perform MS precursor ion search.

    Args:
        context (str): The search context (e.g., 'MB', 'LIPIDS', 'REFMET').
        mz (float): The m/z value.
        adduct (str): The ion adduct type.
        tolerance (float): Mass tolerance in Daltons.

    Returns:
        dict: A dictionary containing the search results or an error message.
    """
    return _get(f"moverz/{context}/{mz}/{adduct}/{tolerance}")


def get_exact_mass(lipid_abbreviation: str, adduct: str) -> dict[str, Any]:
    """Calculate the exact mass (m/z) of an ion of a lipid abbreviation.

    Args:
        lipid_abbreviation (str): The lipid bulk abbreviation.
        adduct (str): The ion adduct type.

    Returns:
        dict: A dictionary containing the exact mass or an error message.
    """
    return _get(f"moverz/exactmass/{lipid_abbreviation}/{adduct}")


def _get(endpoint: str, params: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    """Makes a GET request to the specified endpoint.

    Args:
        endpoint (str): The API endpoint to call.
        params (dict, optional): A dictionary of query parameters. Defaults to None.

    Returns:
        dict: The JSON response from the API.
    """
    url = f"{BASE_URL}/{endpoint}"

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()

        # The API returns data as a list of objects or a single object
        return response.json()

    except requests.exceptions.RequestException as e:
        return {"error": f"API request failed: {str(e)}"}
    except json.JSONDecodeError:
        return {"error": "Failed to parse API response as JSON"}
