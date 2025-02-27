def get_search_url(search_query: str, num_results: int = 1000):
    return f"https://libgen.li/index.php?req={search_query}&columns%5B%5D=t&objects%5B%5D=f&topics%5B%5D=l&res={num_results}&filesuns=all"


def extract_tables_from_search_page(search_url: str):
    search_page = requests.get(search_url)
    search_soup = BeautifulSoup(search_page.content, "html.parser")
    return search_soup.find_all("table", class_="c")
