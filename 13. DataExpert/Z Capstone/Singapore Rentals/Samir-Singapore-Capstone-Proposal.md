# Project Proposal: Singapore Rental Intelligence Dashboard

---

## Project Description

PRIVATE Residential Rent prices (not public) in Singapore have become some of the highest in the world. A simple appartment can cost as much as $5000 Singapore dollars or $4,500 USD, leaving many to take months to evaluate where they will live. 

There are governmental sites and APIs in Singapore that allow people to query the latest contracts (https://eservice.ura.gov.sg/maps/api/). Through this we can run analytics and spot trends for the best opportunities in near real time.

I want to creaate A geospatial dashboard that visualises private residential rental prices across Singapore using official URA transaction data. Users can explore rental prices by district/zone, track price trends over time per building and zone, and filter by property parameters (room type, floor area etc.). 

A Claude-powered assistant answers natural language queries about the data.

---

## Conceptual Data Model

**Core entities and relationships:**

```
Zone/District (1) ──── (many) Building
Building (1)     ──── (many) RentalTransaction
RentalTransaction      ──── Quarter, Rent, FloorArea, RoomType
RentalMedian           ──── District, RoomType, FloorAreaBand, MedianRent, Period
```

**Entity breakdown:**

| Entity | Key Fields |
|---|---|
| Zone | district_id, district_name, geojson_boundary |
| Building | building_name, district_id, postal_code, lat, lng |
| RentalTransaction | building_id, monthly_rent, floor_area_sqft, no_of_bedrooms, lease_date, quarter |
| RentalMedian | district_id, property_type, floor_area_band, median_rent, ref_period |

---

## Data Sources & Formats

| Source | Endpoint | Format | What it provides |
|---|---|---|---|
| URA API | `PMI_Resi_Rental?refPeriod=24q1` | JSON | Raw quarterly rental transactions |
| URA API | `PMI_Resi_Rental_Median` | JSON | Pre-aggregated median rents by district |
| OneMap API | Geocoding endpoint | JSON | Convert building names/postcodes → lat/lng coordinates |
| URA / data.gov.sg | Planning zone boundaries | GeoJSON | District boundary shapes for the map |

**Authentication:** URA API requires a token — register at their developer portal (free).

---

## Ingestion Strategy

**One-time historical load:**
1. Register for URA API token
2. Loop through quarters from `20q1` → `25q1` calling `PMI_Resi_Rental`
3. Parse and store each transaction in a local database

**Ongoing refresh:**
- URA releases new data quarterly — re-fetch the latest quarter on a schedule

**Geocoding buildings:**
- For each unique building name, call OneMap API to get lat/lng coordinates
- Cache results (buildings don't move — only needs to run once)

**Storage:** SQLite for simplicity at bootcamp level — no server setup required, queryable with standard SQL

**Stack suggestion:**
- Python script for ingestion
- SQLite database
- React + Leaflet.js frontend
- Flask or FastAPI backend
- Claude API for natural language Q&A layer

---

## Data Quality Checks

| Check | What to catch |
|---|---|
| Null values | Missing rent, floor area, or district fields |
| Outlier rents | Flag transactions below $500 or above $50,000/month |
| Invalid districts | Validate district codes against known Singapore D01–D28 list |
| Duplicate transactions | Deduplicate by building + lease date + rent + floor area |
| Geocoding failures | Log buildings where OneMap returns no result — review manually |
| Quarter format validation | Ensure `refPeriod` values follow expected `YYqQ` format |

---

## Success Metrics

**Functional:**
- [ ] Map renders all Singapore districts with rental price colour-coding
- [ ] User can click a zone and see average rent, trend line, and building breakdown
- [ ] Filters work for: number of bedrooms, floor area range, time period
- [ ] Trend chart shows at least 5 quarters of historical data per building/zone
- [ ] Claude assistant correctly answers at least 5 test questions (e.g. *"Which district had the highest rent increase in 2024?"*)

**Data:**
- [ ] At least 3 years of historical data loaded (2022–2025)
- [ ] 90%+ of buildings successfully geocoded
- [ ] Zero duplicate transactions in database

**UX:**
- [ ] Latency: Dashboard loads under 3 seconds
- [ ] Mobile-readable (basic responsiveness)
- [ ] Map features all responsivenes
- [ ] Dashboard features and filters all responsive
