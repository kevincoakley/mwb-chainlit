from io import StringIO

import pandas as pd
import requests
import json

BASE_URL = "https://www.metabolomicsworkbench.org/rest"


def get_study_summary(study_id: str = "ST") -> dict:
    """
    Fetch summary information for a study

    Parameters:
    study_id (str): The study ID to fetch. Can be a specific ID like 'ST000001'
                    or a partial ID like 'ST0004' to fetch multiple studies.
                    Defaults to 'ST' which retrieves all studies.

    Returns:
    dict: A dictionary containing the study summary or an error message.
    """
    return _get(f"study/study_id/{study_id}/summary")


def get_study_analysis_information(study_id: str = "ST") -> dict:
    """
    Fetch analysis information for a study

    Parameters:
    study_id (str): The study ID to fetch. Can be a specific ID like 'ST000001'
                    or a partial ID like 'ST0004' to fetch multiple studies.
                    Defaults to 'ST' which retrieves all studies.

    Returns:
    dict: A dictionary containing the study analysis information or an error message.
    """
    return _get(f"study/study_id/{study_id}/analysis")


def get_analysis_datatable(analysis_id: str = "AN") -> pd.DataFrame:
    """
    Fetch analysis datatable for an analysis ID and return it as a DataFrame.

    Parameters:
    analysis_id (str): The analysis ID to fetch. Can be a specific ID like
                       'AN000001' or a partial ID like 'AN0004' to fetch
                       multiple analyses. Defaults to 'AN' which retrieves all
                       analyses.

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


def _get(endpoint, params=None):
    """
    Makes a GET request to the specified endpoint.

    Parameters:
    endpoint (str): The API endpoint to call.
    params (dict, optional): A dictionary of query parameters. Defaults to None.

    Returns:
    dict: The JSON response from the API.
    """
    url = f"{BASE_URL}/{endpoint}"

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()  # Raise an exception for bad status codes

        # The API returns data as a list of studies
        return response.json()

    except requests.exceptions.RequestException as e:
        return {"error": f"API request failed: {str(e)}"}
    except json.JSONDecodeError:
        return {"error": "Failed to parse API response as JSON"}
