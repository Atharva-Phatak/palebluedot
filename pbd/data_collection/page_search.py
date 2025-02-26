import requests
from bs4 import BeautifulSoup
import pandas as pd
from typing import Callable, Pattern, Optional
from enum import Enum
import re


def html_to_pandas(
    html: str,
    ignore_header: bool = False,
    custom_header: Optional[list[str]] = None,
    hyperlink_columns: list[int] = [],
) -> pd.DataFrame:
    """
    Converts HTML document to a pandas dataframe.

    The largest table in the HTML document is assumed to be the table of interest.
    If no tables are found, None is returned.

    Parameters
    ----------
    html : str
        HTML document to convert to pandas dataframe
    ignore_header : bool, optional
        whether to ignore the first row of the table
    custom_header : list[str], optional
        list of column names to append at the top of the table
    hyperlink_columns : list[int], optional
        list of column names that contain hyperlinks; The content in these columns will be replaced with the URLs.

    Returns
    -------
    pd.DataFrame
        pandas dataframe containing the table of interest
    """

    # Parse HTML using BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")

    # Find all tables in the HTML
    tables = soup.find_all("table")

    if not tables:
        # No tables found
        return None

    # Find the largest table based on the number of rows
    largest_table: BeautifulSoup = max(
        tables, key=lambda table: len(table.find_all(["tr", "th", "td"]))
    )

    # Extract data from the table
    data = []
    row: BeautifulSoup
    for row in largest_table.find_all("tr"):
        row_data = row.find_all(["th", "td"])

        # Stringify each cell.
        for i, cell in enumerate(row_data):
            if i in hyperlink_columns:
                # Replace <a> tags in hyperlink columns with URLs they point to.
                hyperlinks = cell.find_all("a")
                if hyperlinks:
                    # If hyperlink is found, replace with its URL
                    for hyperlink in hyperlinks:
                        hyperlink.replace_with(" [" + hyperlink.get("href") + "] ")

            # Replace cell with its text content
            row_data[i] = cell.get_text(strip=True)

        data.append(row_data)

    if ignore_header:
        # Remove the header row
        data.pop(0)

    if custom_header:
        # Append custom column names to the top of the table
        data.insert(0, custom_header)

    # Convert data to Pandas DataFrame
    return pd.DataFrame(data[1:], columns=data[0], index=None)


def multi_page_search(
    url_generator: Callable[[int], str],
    columns: list[str],
    hyperlink_columns: list[str] = [],
    filter: dict[Enum, Pattern] = {},
    limit: int = 100,
    chunk_callback: Optional[Callable[[pd.DataFrame], None]] = None,
) -> pd.DataFrame:
    """
    Concatenates multiple pages of results into a single pandas dataframe.

    Parameters
    ----------
    url_generator : Callable[[int], str]
        function that takes a page number and returns a URL to that page
    columns : list[str]
        list of column names in the table
    hyperlink_columns : list[str]
        list of column names that contain hyperlinks
    filter : dict[FictionColumns, Pattern], optional
        regex to search for in each column of the results; Filtered-out items do not count towards the limit.
    limit : int
        maximum number of items to return; Set to enormous number to get all results.
    chunk_callback : Callable[[pd.DataFrame], None], optional
        function to be called on each new chunk of results; Useful for saving results to a file.

    Returns
    -------
    pd.DataFrame
        a pandas DataFrame containing the results
    """

    dfs = []
    count = 0

    i = 1
    while True:
        url = url_generator(i)
        html = requests.get(url).text
        df = html_to_pandas(
            html,
            ignore_header=True,
            custom_header=columns,
            hyperlink_columns=hyperlink_columns,
        )

        # If no tables were found or dataframe is empty, we have reached the end of the results.
        if df is None or df.empty:
            break

        # Filter the dataframe.
        for column, query in filter.items():
            # df = df[df[column.value].str.contains(query, case=False)]
            for index, row in df.iterrows():
                if not re.search(query, row[column.value]):
                    df.drop(index, inplace=True)

        # Call the callback function on the dataframe.
        if chunk_callback is not None:
            chunk_callback(df)

        # Append the dataframe to the results.
        dfs.append(df)
        count += len(df)

        # If the number of results exceeds the limit, stop.
        if count >= limit:
            break

        i += 1

    if len(dfs) > 0:
        df = pd.concat(dfs).head(limit)
    else:
        df = pd.DataFrame(columns=columns)

    return df
