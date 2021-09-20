# uascrape

Quick and dirty tool to scrape auction data from a local aucion place. I don't expect this is actually usefor for anyone else ever, but it might work on other similar services with some tweaking to the variables. It'll spit out CSV on stdout for crunching with other tools, or the --json flag can be specified to save the scrape results to a JSON file.

## Usage

main.py [--json JSON] event_id

positional arguments:
  event_id

optional arguments:
  --json JSON  Save results in json format to [JSON]
