from bs4 import BeautifulSoup
from pbd.steps.data_collection.validation import ExtractedData
import requests
import zenml


def get_libgen_url(book_name: str) -> str:
    url = f"https://libgen.gs/search.php?&res=100&req={book_name}&phrase=1&view=simple&column=def&sort=year&sortmode=DESC"
    return url


@zenml.task(name="extract_pdf_links")
def extract_pdf_links(book_names: list[str]) -> list[ExtractedData]:
    """
    Extract download links for PDF versions of books from HTML table.

    Args:
        html_content (str): HTML content containing the book table

    Returns:
        list: List of dictionaries containing book title, extension, and download links
    """
    for book_name in book_names:
        # Parse the HTML
        html_content = requests.get(get_libgen_url(book_name)).content
        soup = BeautifulSoup(html_content, "html.parser")

        # Find all rows in the table
        rows = soup.find_all(
            "tr", bgcolor=True
        )  # Using bgcolor attribute to find data rows

        # Store PDF links
        pdf_links = []

        # Process each row
        for row in rows:
            # Extract file extension
            extension_cell = row.find_all("td")[8]  # 9th column has the extension
            extension = extension_cell.text.strip()

            # Only process PDF files
            if extension == "pdf":
                # Extract book title
                title_cell = row.find_all("td")[2]
                title = title_cell.text.strip()

                # Extract download links
                link_cells = row.find_all("td")[
                    9:11
                ]  # 10th and 11th columns have the download links
                link_to_use = None
                for link_cell in link_cells:
                    a_tag = link_cell.find("a")
                    if (
                        a_tag
                        and "href" in a_tag.attrs
                        and "books.ms" in a_tag["href"]
                        and link_to_use is None
                    ):
                        link_to_use = a_tag["href"]
                        break
                # Add to our results
                pdf_links.append(
                    ExtractedData(title=title, extension=extension, links=link_to_use)
                )
        return pdf_links
