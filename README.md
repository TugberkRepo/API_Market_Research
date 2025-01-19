# API_Market_Research
# Dockerized Product Data Project

A portable, **Docker-based** system for **pulling daily product data** from an external API, storing it in **MySQL**, and offering an **interactive Streamlit dashboard** for visualization and exploration.

## Table of Contents

- [Features](#features)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Installation & Usage](#installation--usage)
- [Environment Variables](#environment-variables)
- [Screenshots (Optional)](#screenshots-optional)
- [Future Improvements](#future-improvements)
- [License](#license)

---

## Features

- **Daily Data Ingestion**  
  - A Python script (e.g., `final_dev.py`) calls an external API to fetch product data, performs cleaning, and saves the results into MySQL.  

- **MySQL Database Container**  
  - All data is managed via a Dockerized MySQL 8.0 service, with volumes for persistent storage.  
  - Ensures reliable, consistent data between runs.

- **Streamlit Dashboard**  
  - Filters: Easily narrow down data by categories, part numbers, manufacturers, distributors, etc.  
  - Aggregated charts (bar or line) for insights like average prices by distributor.  
  - Single-part view showing product images, buy links, and time-based price charts.  
  - Consistent color mapping for distributors across charts.

- **Docker Compose Orchestration**  
  - One command (`docker-compose up --build`) starts the entire system on any machine with Docker.  
  - Makes the environment fully **portable** and **reproducible**.

---

## Project Structure

