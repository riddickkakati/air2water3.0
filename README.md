# Aqualite Engine Backend

## 🌊 About The Project

Aqualite Engine 1.0 is a comprehensive water quality monitoring and forecasting platform. It provides a unified model structure for both lake and river thermal dynamics, integrating and extending the functionalities of air2water (lakes) and air2stream (rivers) models.

The platform consists of three main modules:

1. **Forecasting**: Temperature prediction using hybrid physics-based/statistical models 
2. **Monitoring**: Water quality monitoring via Google Earth Engine satellite data 
3. **Machine Learning**: Data-driven water temperature prediction using state-of-the-art ML algorithms 

Aqualite Engine 1.0 serves as a one-stop solution for water resources management, providing satellite-based monitoring, accurate forecasting, and advanced analysis capabilities.

This Django-based application allows researchers, water resource managers, and environmental scientists to analyze water temperatures, predict future trends, and monitor water quality parameters like chlorophyll-a, turbidity, and dissolved oxygen.

## 🚀 Key Features

- **Unified Framework**: A single platform for both lake and river water quality analysis 
- **Web Interface**: Full-featured web interface with local Django server 
- **Real-time Monitoring**: Satellite-based water quality parameter estimation using Google Earth Engine 
- **Advanced Forecasting**: Physics-based models with stochastic calibration 
- **Machine Learning Integration**: Multiple algorithms with automated selection of best performer 
- **Collaborative Environment**: Group-based project management with chat functionality 
- **Interactive Visualization**: Comprehensive data visualization tools 
- **Local Data Storage**: All data stored locally in SQLite database 

## 📋 Prerequisites

Before you begin, ensure you have the following installed:

- Python 3.10
- Google Earth Engine account and API key (for monitoring module) 
- SQLite (included with Python) 
- Node.js and npm (for frontend development. More details in the frontend repository.)

## 🔧 Installation

### Complete Local Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/riddickkakati/air2water3.0.git
   cd air2water3.0
   ```

2. **Create and activate a virtual environment** (with Python 3.10):
   ```bash
   # First ensure you have Python 3.10 installed
   # You can download it from https://www.python.org/downloads/release/python-31010/
   
   # Create virtual environment with Python 3.10
   python3.10 -m venv venv
   
   # On Windows
   venv\Scripts\activate
   
   # On macOS/Linux
   source venv/bin/activate
   
   # Verify Python version
   python --version
   # Should output: Python 3.10.x
   ```

3. **Install required Python packages**:
   ```bash
   pip install -r requirements.txt
   ```
   
   If you don't have a requirements.txt file, here are the essential packages:
   ```bash
   pip install django==5.1.4 djangorestframework django-cors-headers pillow google-api-python-client \
   google-auth google-auth-httplib2 google-auth-oauthlib earthengine-api folium matplotlib numpy \
   pandas scikit-learn tensorflow xgboost catboost pyyaml plotly==5.14.1
   ```

4. **Setup Google Earth Engine authentication**:
   - Create a service account in [Google Cloud Console](https://console.cloud.google.com/)
   - Enable the Earth Engine API 
   - Create and download a JSON key for your service account 
   - Save the key in a secure location on your computer 

5. **Configure local settings**:
   - In the `settings.py` file, ensure your configuration matches your local environment:
     ```python
     DEBUG = True
     ALLOWED_HOSTS = ['127.0.0.1', 'localhost']
     
     # Set media and static file paths
     STATIC_URL = '/staticfiles/'
     STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
     MEDIA_URL = '/mediafiles/'
     MEDIA_ROOT = os.path.join(BASE_DIR, 'mediafiles')
     ```

6. **Create necessary directories**:
   ```bash
   mkdir -p mediafiles/monitoring mediafiles/results mediafiles/ml_results staticfiles
   ```

7. **Set up the database**:
   ```bash
   python manage.py makemigrations forecasting
   python manage.py makemigrations monitoring
   python manage.py makemigrations machinelearning
   python manage.py migrate
   ```

8. **Create a superuser** (for admin access):
   ```bash
   python manage.py createsuperuser
   ```
   Follow the prompts to create your admin username, email, and password.

9. **Run the development server**:
   ```bash
   python3 manage.py runserver
   ```

10. **Access the application**:
    - Django admin interface: http://127.0.0.1:8000/admin/ 
    - API endpoints: 
        - Forecasting: http://127.0.0.1:8000/forecasting/ 
        - Monitoring: http://127.0.0.1:8000/monitoring/ 
        - Machine Learning: http://127.0.0.1:8000/machinelearning/ 

## 🏗️ Project Structure (Important files only)

```
Air2water3.0/
├── db.sqlite3 (Database)
├── forecasting (Forecasting scripts directory)
│   ├── admin.py (Django source file)
│   ├── air2water (air2water module)
│   │   ├── Air2water.py (air2water/air2stream main script)
│   │   ├── calibrators (calibrators for air2water/air2stream)
│   │   │   ├── LHS_python_riddick_sebastiano.py (Latinhypercube script)
│   │   │   ├── MC_python_riddick_sebastiano.py (Random sampling script)
│   │   │   ├── Parameters.py (air2water parameters processing script)
│   │   │   ├── PSO_python_riddick_sebastiano.py (PSO script)
│   │   │   └── spotpy_params_air2water_air2stream.py (Spotpy spotsetup file)
│   │   ├── config (Configuration files from air2water script directory)
│   │   ├── core.py (Core script linking to cython/fortran)
│   │   ├── cython_modules.pyx (cython core script)
│   │   ├── fortran_modules.f90 (fortran core script)
│   │   ├── fullparameterset.mat (Automatic parameter ranges estimator file)
│   │   ├── __init__.py (Python module initialization source file)
│   │   ├── IO (Input Output directory)
│   │   │   ├── filter_db.py (Database filter script)
│   │   │   ├── __init__.py (Python module initialization source file)
│   │   │   ├── Interpolator.py (Missing data interpolation script)
│   │   │   ├── Send_emails.py (Email sending script)
│   │   │   ├── UUID_Generator.py (Script to generate Unique ID)
│   │   │   └── yaml_parser.py (Script to process .yaml files)
│   ├── apps.py (Django source file)
│   ├── __init__.py (Python module initialization source file)
│   ├── migrations (Django migrations directory)
│   ├── models.py (Django source file)
│   ├── serializers.py (Django source file)
│   ├── tests.py (Django source file)
│   ├── urls.py (Django source file)
│   └── views.py (Django source file)
├── LICENSE (License file)
├── machinelearning (Machine learning scripts directory)
│   ├── admin.py (Django source file)
│   ├── Air2waterML (Main scripts directory)
│   │   ├── Air2water.py (Machine learning main script)
│   │   ├── __init__.py (Python module initialization source file)
│   │   ├── IO (Input Output directory)
│   │   │   ├── __init__.py (Python module initialization source file)
│   │   │   ├── Interpolator.py (Missing data interpolation script)
│   │   │   └── Send_emails.py (Email sending script)
│   ├── apps.py (Django source file)
│   ├── __init__.py (Python module initialization source file)
│   ├── migrations (Django migrations directory)
│   ├── models.py (Django source file)
│   ├── serializers.py (Django source file)
│   ├── tests.py (Django source file)
│   ├── urls.py (Django source file)
│   └── views.py (Django source file)
├── manage.py (Django source file)
├── mediafiles (Results directory)
├── monitoring (Monitoring script directory)
│   ├── admin.py (Django source file)
│   ├── Air2water_GEE.py (Monitoring core script using Google Earth Engine)
│   ├── apps.py (Django source file)
│   ├── __init__.py (Python module initialization source file)
│   ├── migrations (Django migrations directory)
│   ├── models.py (Django source file)
│   ├── serializers.py (Django source file)
│   ├── tests.py (Django source file)
│   ├── urls.py (Django source file)
│   └── views.py (Django source file)
├── ProjectFiles
│   ├── asgi.py (Django source file)
│   ├── __init__.py (Python module initialization source file)
│   ├── settings.py (Django source file)
│   ├── urls.py (Django source file)
│   └── wsgi.py (Django source file)
├── README.md (Readme file)
└── requirements.txt (Installation requirements file)
```

## 🌟 Modules Overview

### Forecasting Module

The forecasting module provides temperature prediction using the air2water (for lakes) and air2stream (for rivers) models. It includes:

- Parameter optimization using PSO, Latin Hypercube, and Monte Carlo methods 
- Support for various error metrics (RMSE, KGE, NSE) 
- Time series data handling with interpolation options 
- Forward simulation and calibration modes 
- Visualization of calibration/validation results 

### Monitoring Module

The monitoring module leverages Google Earth Engine to provide real-time water quality monitoring. Features include:

- Chlorophyll-a index (NDCI) calculation 
- Turbidity index (NDTI) calculation 
- Dissolved oxygen estimation 
- Interactive map visualization and download

### Machine Learning Module

The ML module applies various algorithms to predict water temperature:

- Support Vector Regression 
- Random Forest 
- Decision Trees 
- XGBoost 
- CatBoost 
- Deep Learning (ANN) 
- Dimensionality reduction techniques (PCA, KPCA, LDA) 
- Automated model selection and hyperparameter tuning 

## 📊 Usage Examples (test parameters)

### Forecasting Water Temperature

```python
# Initialize the model
model = Air2water_OOP(
    interpolate=True,
    n_data_interpolate=7,
    validation_required="Uniform Percentage",
    percent=10,
    model="air2water",
    method="SpotPY",
    mode="calibration",
    error="RMSE",
    optimizer="PSO"
)

# Run the simulation
model.run()
```

### Monitoring Water Quality

```python
# Initialize the monitoring system
monitor = Air2water_monit(
    start_date='2022-01-01',
    end_date='2022-01-31',
    long=45.667,
    lat=10.683,
    cc=7,
    satellite=2,  # Sentinel
    variable=1,   # Chlorophyll-a
    service_account='your-service-account@project.iam.gserviceaccount.com',
    service_key='/path/to/service-key.json'
)

# Generate interactive map
map_html = monitor.run()
```

### Machine Learning Analysis

```python
# Initialize the ML model
ml_model = ML_Model(
    model="air2water",
    interpolate=True,
    n_data_interpolate=7,
    validation_required="Random Percentage",
    percent=20,
    air2waterusercalibrationpath="/path/to/data.txt"
)

# Run analysis
results = ml_model.run()
```

## 🚀 Getting Started

Once you have the application installed, follow these steps to start using Aqualite Engine backend independently:

### 1. Access the Admin Panel

1. Navigate to http://127.0.0.1:8000/admin/ 
2. Login with the superuser credentials you created during installation 
3. You can manage users, groups, and other model data from here 

### 2. Using the Forecasting Module

1. Create a forecasting group from the web interface 
2. Upload your timeseries data (temperature and meteorological data) 
3. Configure your model parameters: 
   - Select between air2water (lake) or air2stream (river) models 
   - Choose optimization method (PSO, Latin Hypercube, Monte Carlo) 
   - Set validation parameters and error metrics 
4. Run the simulation and view the results 

### 3. Using the Monitoring Module

1. Create a monitoring group 
2. Configure your monitoring parameters: 
   - Set date range for analysis 
   - Select geographical location (latitude/longitude) 
   - Choose satellite data source (Landsat or Sentinel) 
   - Select water quality parameter (Chlorophyll-a, Turbidity, or Dissolved Oxygen) 
3. Provide your Google Earth Engine service account credentials 
4. Run the monitoring process to generate interactive maps 

### 4. Using the Machine Learning Module

1. Create a machine learning group 
2. Upload your training data 
3. Configure model parameters: 
   - Choose between air2water or air2stream data structure 
   - Set validation options 
   - Configure interpolation settings 
4. Run the analysis to evaluate multiple machine learning algorithms 
5. View results showing the best-performing model with performance metrics 

### 5. Data Formats

For time series data, use a tab-separated text file with the following format:

```
# For air2water (lake) model:
# date    air_temperature    water_temperature
2020-01-01    5.2    8.3
2020-01-02    4.8    8.1
...
```

Sample data links:
- [calibration](#)
- [validation](#)
- [parameter ranges](#)
- [forward parameters](#)

```
# For air2stream (river) model:
# date    air_temperature    water_temperature    discharge
2020-01-01    5.2    8.3    12.5
2020-01-02    4.8    8.1    13.2
...
```

Sample data links:
- [calibration](#)
- [validation](#)
- [parameter ranges](#)

## 📖 Working demonstration

For a working demonstration of the interface, please refer to the [YouTube link](#).

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the project 
2. Create your feature branch (`git checkout -b feature/AmazingFeature`) 
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`) 
4. Push to the branch (`git push origin feature/AmazingFeature`) 
5. Open a Pull Request 

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 📧 Contact

Project Lead - [riddick.kakati93@gmail.com](mailto:riddick.kakati93@gmail.com)

## 🙏 Acknowledgments

- Original air2water model by S. Piccolroaz 
- Original air2stream model by M. Toffolon and S. Piccolroaz 
- Google Earth Engine team for GEE API 
- AWS and Firebase for cloud infrastructure
