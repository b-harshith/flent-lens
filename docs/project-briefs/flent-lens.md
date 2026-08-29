# Flent Lens Rental Opportunity Project

## Overview

Flent Lens was a personal market-research project where I tried to test a co-living rental arbitrage thesis using real MagicBricks rental listings. The idea was to check whether larger apartments could be leased and converted into individual room inventory at price points that made sense against nearby 1BHK alternatives.

The starting question was:

> Can someone lease larger apartments, convert them into individual room inventory, and price them competitively against nearby 1BHK alternatives?

Instead of only thinking about the model conceptually, I wanted to test the thesis with actual listing data. The project compared 1BHK rent signals with nearby 3BHK+ rental supply and used that to identify zones where the economics looked more promising for deeper validation.

## Approach

The project became a geospatial opportunity lens for rental arbitrage. I looked at rental supply, pricing, and spatial density to rank areas where the model might be worth investigating further.

The analysis focused on:

- 1BHK rent levels as a proxy for what individual renters might pay
- 3BHK+ rental supply as possible conversion inventory
- Locality and pincode-level clustering
- Ward or zone-level opportunity ranking
- Data checks to avoid treating every listing as equally reliable

## Data collection

The scraping process was built through observation and iteration. Instead of manually copying listings, I inspected how MagicBricks loaded rental results in the browser, watched the network requests behind the listing pages, and identified the request patterns that returned structured listing data.

From there, the workflow was:

- Capture and study the relevant network requests
- Understand the query parameters, pagination, and returned JSON structure
- Parse listing fields such as rent, BHK type, location, coordinates, area, furnishing, and availability
- Clean and normalize the extracted listings into a usable dataset
- Use the dataset to compare rent levels and supply depth across locations

This was not designed as a perfect industrial scraper. It was a research-oriented data collection workflow built to answer a specific business question quickly and honestly.

## My role

My strongest contribution was the thinking process: breaking a business thesis into measurable assumptions, figuring out how to collect useful market data, and iterating until the output could support a decision.

I used AI tools and an AI-assisted IDE throughout the project to understand code paths faster, prototype parsing logic, debug data-cleaning issues, and move from raw listings to a structured analysis. The project was less about claiming to build a production-grade system and more about showing that I could use modern tools to investigate a real business model with data.

## What I focused on

- Converting a business model into testable assumptions
- Learning from browser and network behavior to collect usable data
- Comparing local supply and pricing patterns instead of relying only on intuition
- Using AI-assisted workflows to move faster while still checking the logic manually

## What I learned

The biggest learning was that even a simple business idea becomes much clearer when it is translated into measurable assumptions. Flent Lens helped me practice moving from an idea to data collection, cleaning, comparison, and a more evidence-based view of whether the model deserved further exploration.

