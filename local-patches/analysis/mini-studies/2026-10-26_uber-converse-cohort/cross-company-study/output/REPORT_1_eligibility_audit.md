# Report 1 — Eligibility and source audit

Eligible file pairs: **41** / 41 candidates.

Discovery ticker **UBER** retained in universe snapshot but excluded from evaluation.

## Partition (frozen before results)

| ticker   | bucket         | stage       |
|:---------|:---------------|:------------|
| ABNB     | Consumer       | pilot       |
| CMCSA    | Consumer       | pilot       |
| DIS      | Consumer       | development |
| MCD      | Consumer       | development |
| NFLX     | Consumer       | development |
| RBLX     | Consumer       | development |
| SBUX     | Consumer       | development |
| SPOT     | Consumer       | holdout     |
| TSLA     | Consumer       | holdout     |
| WMT      | Consumer       | holdout     |
| BAC      | Finance_Health | pilot       |
| BLK      | Finance_Health | pilot       |
| BNTX     | Finance_Health | development |
| COIN     | Finance_Health | development |
| HOOD     | Finance_Health | development |
| JPM      | Finance_Health | development |
| MRNA     | Finance_Health | development |
| MS       | Finance_Health | holdout     |
| PFE      | Finance_Health | holdout     |
| UNH      | Finance_Health | holdout     |
| BA       | Industrials    | pilot       |
| DAL      | Industrials    | pilot       |
| F        | Industrials    | development |
| FDX      | Industrials    | development |
| GM       | Industrials    | development |
| LMT      | Industrials    | development |
| LUV      | Industrials    | development |
| STLA     | Industrials    | holdout     |
| TM       | Industrials    | holdout     |
| UAL      | Industrials    | holdout     |
| AAPL     | Technology     | pilot       |
| ADBE     | Technology     | pilot       |
| AMD      | Technology     | development |
| AMZN     | Technology     | development |
| CRM      | Technology     | development |
| DELL     | Technology     | development |
| GOOGL    | Technology     | development |
| META     | Technology     | holdout     |
| MSFT     | Technology     | holdout     |
| NVDA     | Technology     | holdout     |

## Audit sample

| ticker   | bucket     | executive         | dob        | dob_parse_ok   | verification_status     | tenure_note                                         | dob_source_url                                                                            | earnings_csv                                                                                 | ohlc_csv                                                                                                      | has_earnings   | has_ohlc   | eligible_files   |
|:---------|:-----------|:------------------|:-----------|:---------------|:------------------------|:----------------------------------------------------|:------------------------------------------------------------------------------------------|:---------------------------------------------------------------------------------------------|:--------------------------------------------------------------------------------------------------------------|:---------------|:-----------|:-----------------|
| MSFT     | Technology | Satya Nadella     | 1967-08-19 | True           | Secondary corroboration | Long-tenured CEO                                    | https://www.wikidata.org/wiki/Q7426870                                                    | /Users/thomasbikeev/Projects/listok_fd/finance_data_downloader/data/eodhd_earnings/MSFT.csv  | /Users/thomasbikeev/Projects/listok/finance-data-downloader/finance_data_downloader/data/eodhd_ohlc/MSFT.csv  | True           | True       | True             |
| AAPL     | Technology | Tim Cook          | 1960-11-01 | True           | Strong                  | CEO through August 2026                             | https://encyclopediaofalabama.org/article/tim-cook/                                       | /Users/thomasbikeev/Projects/listok_fd/finance_data_downloader/data/eodhd_earnings/AAPL.csv  | /Users/thomasbikeev/Projects/listok/finance-data-downloader/finance_data_downloader/data/eodhd_ohlc/AAPL.csv  | True           | True       | True             |
| NVDA     | Technology | Jensen Huang      | 1963-02-17 | True           | Secondary corroboration | Founder CEO                                         | https://en.wikipedia.org/wiki/Jensen_Huang                                                | /Users/thomasbikeev/Projects/listok_fd/finance_data_downloader/data/eodhd_earnings/NVDA.csv  | /Users/thomasbikeev/Projects/listok/finance-data-downloader/finance_data_downloader/data/eodhd_ohlc/NVDA.csv  | True           | True       | True             |
| GOOGL    | Technology | Sundar Pichai     | 1972-06-10 | True           | Secondary corroboration | Alphabet CEO from 2019                              | https://en.wikipedia.org/wiki/Sundar_Pichai                                               | /Users/thomasbikeev/Projects/listok_fd/finance_data_downloader/data/eodhd_earnings/GOOGL.csv | /Users/thomasbikeev/Projects/listok/finance-data-downloader/finance_data_downloader/data/eodhd_ohlc/GOOGL.csv | True           | True       | True             |
| META     | Technology | Mark Zuckerberg   | 1984-05-14 | True           | Secondary corroboration | Founder CEO                                         | https://en.wikipedia.org/wiki/Mark_Zuckerberg                                             | /Users/thomasbikeev/Projects/listok_fd/finance_data_downloader/data/eodhd_earnings/META.csv  | /Users/thomasbikeev/Projects/listok/finance-data-downloader/finance_data_downloader/data/eodhd_ohlc/META.csv  | True           | True       | True             |
| AMZN     | Technology | Andy Jassy        | 1968-01-13 | True           | DOB needs second source | Amazon CEO from July 2021                           | https://en.wikipedia.org/wiki/Andy_Jassy                                                  | /Users/thomasbikeev/Projects/listok_fd/finance_data_downloader/data/eodhd_earnings/AMZN.csv  | /Users/thomasbikeev/Projects/listok/finance-data-downloader/finance_data_downloader/data/eodhd_ohlc/AMZN.csv  | True           | True       | True             |
| CRM      | Technology | Marc Benioff      | 1964-09-25 | True           | Secondary corroboration | Founder CEO                                         | https://www.wikidata.org/wiki/Q1521908                                                    | /Users/thomasbikeev/Projects/listok_fd/finance_data_downloader/data/eodhd_earnings/CRM.csv   | /Users/thomasbikeev/Projects/listok/finance-data-downloader/finance_data_downloader/data/eodhd_ohlc/CRM.csv   | True           | True       | True             |
| AMD      | Technology | Lisa Su           | 1969-11-07 | True           | Strong                  | CEO since 2014                                      | https://www.munzinger.de/register/portrait/biographien/su%20lisa/00/32264                 | /Users/thomasbikeev/Projects/listok_fd/finance_data_downloader/data/eodhd_earnings/AMD.csv   | /Users/thomasbikeev/Projects/listok/finance-data-downloader/finance_data_downloader/data/eodhd_ohlc/AMD.csv   | True           | True       | True             |
| ADBE     | Technology | Shantanu Narayen  | 1963-05-27 | True           | Secondary corroboration | CEO since 2007                                      | https://en.wikipedia.org/wiki/Shantanu_Narayen                                            | /Users/thomasbikeev/Projects/listok_fd/finance_data_downloader/data/eodhd_earnings/ADBE.csv  | /Users/thomasbikeev/Projects/listok/finance-data-downloader/finance_data_downloader/data/eodhd_ohlc/ADBE.csv  | True           | True       | True             |
| DELL     | Technology | Michael Dell      | 1965-02-23 | True           | Strong                  | Founder CEO                                         | https://achievement.org/achiever/michael-dell/                                            | /Users/thomasbikeev/Projects/listok_fd/finance_data_downloader/data/eodhd_earnings/DELL.csv  | /Users/thomasbikeev/Projects/listok/finance-data-downloader/finance_data_downloader/data/eodhd_ohlc/DELL.csv  | True           | True       | True             |
| UBER     | Consumer   | Dara Khosrowshahi | 1969-05-28 | True           | Existing study          | Discovery company; exclude from new-company holdout | nan                                                                                       | /Users/thomasbikeev/Projects/listok_fd/finance_data_downloader/data/eodhd_earnings/UBER.csv  | /Users/thomasbikeev/Projects/listok/finance-data-downloader/finance_data_downloader/data/eodhd_ohlc/UBER.csv  | True           | True       | True             |
| ABNB     | Consumer   | Brian Chesky      | 1981-08-29 | True           | Strong                  | Founder CEO                                         | https://acclad.org/brian-chesky                                                           | /Users/thomasbikeev/Projects/listok_fd/finance_data_downloader/data/eodhd_earnings/ABNB.csv  | /Users/thomasbikeev/Projects/listok/finance-data-downloader/finance_data_downloader/data/eodhd_ohlc/ABNB.csv  | True           | True       | True             |
| TSLA     | Consumer   | Elon Musk         | 1971-06-28 | True           | Secondary corroboration | CEO since 2008                                      | https://en.wikipedia.org/wiki/Elon_Musk                                                   | /Users/thomasbikeev/Projects/listok_fd/finance_data_downloader/data/eodhd_earnings/TSLA.csv  | /Users/thomasbikeev/Projects/listok/finance-data-downloader/finance_data_downloader/data/eodhd_ohlc/TSLA.csv  | True           | True       | True             |
| DIS      | Consumer   | Bob Iger          | 1951-02-10 | True           | Secondary corroboration | Intermittent CEO; tenure differs across years       | https://en.wikipedia.org/wiki/Bob_Iger                                                    | /Users/thomasbikeev/Projects/listok_fd/finance_data_downloader/data/eodhd_earnings/DIS.csv   | /Users/thomasbikeev/Projects/listok/finance-data-downloader/finance_data_downloader/data/eodhd_ohlc/DIS.csv   | True           | True       | True             |
| WMT      | Consumer   | Doug McMillon     | 1966-10-17 | True           | Strong                  | CEO through January 2026                            | https://www.ourmidland.com/news/article/Correction-Wal-Mart-CEO-Bio-Box-story-6920291.php | /Users/thomasbikeev/Projects/listok_fd/finance_data_downloader/data/eodhd_earnings/WMT.csv   | /Users/thomasbikeev/Projects/listok/finance-data-downloader/finance_data_downloader/data/eodhd_ohlc/WMT.csv   | True           | True       | True             |