# 🌾 AtmoSync: Micro-Climate Arbitrage Analytics (Agriculture)

**Organization:** Infotact Solutions
**Role:** Data Associate L1 Intern
**Track:** Agro-Climatic Data Analytics, Spatial Modeling & Statistical Validation

AtmoSync is an interactive analytical platform designed to identify, quantify, and analyze micro-climatic growing condition differentials across agricultural zones. By evaluating atmospheric indicators against agronomic crop requirements, AtmoSync identifies locations with potentially improved crop suitability within reasonable geographical distances.

The platform combines climate data processing, crop suitability scoring, spatial analysis, and statistical validation to support agricultural climate analysis.

---

## 📐 Mathematical Formulation

### 1. Crop Suitability Index (CSI)

For an atmospheric parameter \(x \in \{\text{temp}, \text{hum}, \text{rain}, \text{uv}\}\), an ideal agronomic band \([\text{low}, \text{high}]\), and tolerance \(\delta\), the suitability score is calculated as:

\[
S(x)=\text{clip}\left(1-\frac{\max(0,\text{low}-x,x-\text{high})}{\delta},0,1\right)
\]

The composite Crop Suitability Index (CSI), scaled from 0 to 100, is defined as:

\[
\text{CSI}=100\times\sum_i w_i\cdot S(x_i)
\]

Default agronomic weights:

- **Temperature (0.40):** Influences enzymatic reactions and plant metabolic rates.
- **Relative Humidity (0.25):** Influences moisture conditions, vapor pressure deficit, and disease risk.
- **Precipitation (0.20):** Represents rainfall availability for crop water requirements.
- **Solar UV Index (0.15):** Represents solar exposure conditions.

**Supported crops:** Rice, Wheat, Cotton, Maize, Groundnut, and Sugarcane.

### 2. Spatial Arbitrage Finder

Spatial separation between locations A and B is calculated using the Haversine formula.

\[
d=2R\arcsin\left(\sqrt{\sin^2\left(\frac{\Delta\phi}{2}\right)+\cos(\phi_1)\cos(\phi_2)\sin^2\left(\frac{\Delta\lambda}{2}\right)}\right)
\]

Where:

- \(R\) represents the Earth's radius.
- \(\phi_1,\phi_2\) represent latitude coordinates.
- \(\lambda_1,\lambda_2\) represent longitude coordinates.

The Arbitrage Gain relative to an origin location A is defined as:

\[
\Delta CSI_{A\rightarrow B}=CSI_B-CSI_A
\]

This comparison is performed for locations within a specified search radius:

\[
d(A,B)\leq r
\]

The spatial arbitrage finder identifies nearby locations with potentially higher crop suitability scores.

---

## 📂 Project Structure

```text
atmosync-microclimate/
├── app.py
├── make_sample_data.py
├── requirements.txt
├── README.md
├── data/
│   ├── raw/
│   └── processed/
├── notebooks/
│   ├── 01_data_understanding.ipynb
│   └── 02_exploratory_data_analysis.ipynb
├── reports/
│   └── data_dictionary.csv
├── src/
│   ├── __init__.py
│   ├── data_loader.py
│   └── arbitrage.py
└── tests/
    └── test_arbitrage.py
```

### Project Components

- **app.py:** Interactive Streamlit application and dashboard.
- **make_sample_data.py:** Generates synthetic seasonal datasets.
- **requirements.txt:** Project dependencies.
- **data/raw/:** Raw weather datasets and input data.
- **data/processed/:** Cleaned and processed datasets.
- **notebooks/:** Data understanding and exploratory analysis.
- **reports/:** Data documentation and reports.
- **src/data_loader.py:** Data ingestion and inspection utilities.
- **src/arbitrage.py:** Crop suitability and spatial analytical calculations.
- **tests/:** Unit tests for analytical functionality.

---

## 🚀 Getting Started

### 1. Prerequisites

Install Python and ensure it is available from the terminal.

### 2. Create a Virtual Environment

```powershell
python -m venv .venv
```

Activate the virtual environment:

```powershell
.\.venv\Scripts\activate
```

### 3. Install Dependencies

```powershell
pip install -r requirements.txt
```

### 4. Run Unit Tests

```powershell
python -m pytest tests/
```

Alternatively:

```powershell
python tests/test_arbitrage.py
```

### 5. Launch the Dashboard

```powershell
streamlit run app.py
```

The application can be accessed through the local URL displayed in the terminal after launching Streamlit.

---

## 📊 Analytical Features

### 1. Interactive Geospatial Map

Visualizes geographical climate conditions and crop suitability differences across locations.

### 2. Radius Arbitrage Finder

Evaluates nearby locations within a selected geographical search radius and compares crop suitability scores.

### 3. Seasonal Aggregation

Analyzes climate and crop suitability conditions across the following agricultural seasons:

- **Kharif:** June – October
- **Rabi:** November – March
- **Zaid:** April – May

### 4. Statistical Hypothesis Testing

The analytical framework includes statistical methods for evaluating regional and environmental relationships:

- **One-way ANOVA:** Evaluates differences in regional climate or suitability distributions.
- **Welch's two-sample t-test:** Compares two location groups.
- **Pearson correlation:** Examines relationships between environmental indicators.

### 5. Data Cleaning and Auditing

The data processing workflow includes:

- Dataset schema verification.
- Data quality inspection.
- Outlier handling.
- Missing-value handling.
- Data validation and preparation for analysis.

---

## 🔄 Project Workflow

AtmoSync follows a structured data analytics workflow for agro-climatic evaluation.

### Workflow Steps

1. Load weather data from CSV files.
2. Inspect the dataset and verify its structure.
3. Clean and validate the data.
4. Process climate indicators for analytical use.
5. Calculate crop suitability scores.
6. Evaluate geographical distances between locations.
7. Compare suitability scores across locations.
8. Explore analytical results through the Streamlit application.

---

## 📈 Data Processing and Analytical Methodology

The AtmoSync platform follows a structured data analysis workflow to evaluate agro-climatic suitability across geographical locations. Weather data is organized, validated, and analyzed using environmental indicators such as temperature, relative humidity, precipitation, and UV index.

The Crop Suitability Index (CSI) combines weighted environmental parameters to assess crop-specific suitability. Spatial analysis uses geographical distances to identify alternative growing locations within a selected search radius. Statistical validation methods support regional comparisons and analytical interpretation.

The resulting analysis helps explore climate-based agricultural suitability and potential micro-climatic differences between locations.

---

## 🌱 Data Analysis Objective

The primary objective of AtmoSync is to evaluate agro-climatic conditions across geographical locations and identify potential agricultural suitability differences.

The analytical framework considers:

- Environmental conditions and crop requirements.
- Crop-specific suitability scores.
- Geographical proximity between locations.
- Seasonal climatic variations.
- Statistical comparison of environmental indicators.

The platform provides an analytical approach to exploring agricultural suitability based on climate-related data.

---

## 💻 Application Setup and Execution

The AtmoSync application is built using Python and Streamlit.

The application processes climate data and evaluates crop suitability based on selected environmental indicators.

### Running the Application

1. Install the required Python packages using `requirements.txt`.
2. Open the project directory in the terminal.
3. Activate the Python virtual environment.
4. Run the Streamlit application using `app.py`.
5. Access the dashboard through the local browser URL.

### Application Components

- **app.py:** Main application interface and dashboard.
- **src/:** Data processing and climate analysis modules.
- **tests/:** Unit tests for project functionality.
- **data/:** Dataset storage and input files.
- **reports/:** Data documentation and analysis reports.

---

## 📌 Development Progress – November 24, 2026

- Reviewed the AtmoSync project architecture and repository structure.
- Examined the Crop Suitability Index (CSI) mathematical formulation and agronomic weighting parameters.
- Reviewed the spatial arbitrage methodology using the Haversine distance formula.
- Studied the analytical workflow involving data ingestion, cleaning, validation, and climate suitability analysis.
- Reviewed the project testing, dataset organization, and Streamlit application setup.
- Updated project documentation to improve the organization and presentation of analytical methodology and workflow details.

---

## 🎯 Project Goal

AtmoSync aims to provide an analytical framework for exploring micro-climatic variations, comparing crop suitability across geographical locations, and identifying potential agricultural opportunities using climate data, spatial analysis, and statistical validation.

## Dashboard Navigation

The AtmoSync dashboard provides a vertically scrollable interface
for exploring microclimate and agricultural arbitrage analytics.

### Dashboard Sections
- Overview
- Interactive Map
- Arbitrage Finder
- Trends Analysis
- Seasonal Analysis
- Statistical Analysis
- Data Quality

Users can explore all analytics sections on a single page
without switching between tabs.