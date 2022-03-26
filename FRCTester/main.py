from pathlib import Path
import csv
import os
import urllib.parse
import time
import ssl
import certifi
import logging

import asyncio
import aiohttp

from alive_progress import alive_it

BASE_DIR = Path(__file__).resolve().parent
REPORTS_PATH = f'{BASE_DIR}/reports'

SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())
HEADERS = {
    'Content-Type': 'application/json',
    'Authorization': os.environ.get('API_TOKEN')
}

logging.basicConfig(level=logging.INFO)


def main():
    logger = logging.getLogger('FRC TESTER')
    
    queries = get_queries()
    results = asyncio.run(test_api_queries(queries))
    with open(f'{REPORTS_PATH}/report.csv', 'w') as file:
        writer = csv.writer(file)
        # HEADERS
        writer.writerow(['REQUEST_BODY', 'RESPONSE_TIME', 'RESPONSE_CODE', 'ERROR_CODES', 'ERROR_MESSAGES', 'WARNING_CODES', 'WARNING_MESSAGES'])
        
        # ROWS
        for result in results:
            row = []
            # REQUEST_BODY
            row.append(result.get('request_body'))
            
            # RESPONSE_TIME
            row.append("{:.5f}".format(result.get('elapsed_time')))
            
            # RESPONSE_CODE
            row.append(result.get('status_code'))
            
            # ERRORS
            error_codes = ''
            if len(result.get('error_codes')) > 0:
                for error_code in result.get('error_codes'):
                    error_codes += f'{error_code}; '
            error_messages = ''
            if len(result.get('error_messages')) > 0:
                for error_message in result.get('error_messages'):
                    error_messages += f'{error_message}; '
            row.append(error_codes.strip())
            row.append(error_messages.strip())
            
            # WARNINGS
            warning_codes = ''
            if len(result.get('warning_codes')) > 0:
                for warning_code in result.get('warning_codes'):
                    warning_codes += f'{warning_code}; '
            warning_messages = ''
            if len(result.get('warning_messages')) > 0:
                for warning_message in result.get('warning_messages'):
                    warning_messages += f'{warning_message}; '
            row.append(warning_codes.strip())
            row.append(warning_messages.strip())
            
            # ROW WRITE
            writer.writerow(row)
    logger.info(f'Report file created at {REPORTS_PATH}')

def get_queries() -> list:
    queries = []
    with open(f'{BASE_DIR}/frc.csv') as file:
        reader = csv.reader(file, delimiter=',')
        for row in reader:
            if 'flight_calculator' in row[2]:
                queries.append(get_query_data(row[2]))

    return queries


def get_query_data(query: str) -> dict:
    # Getting query parameters
    url = query.split('"')[3]
    url_query = url.split('?')[1]
    url_parameters = url_query.split('&')

    # Generating dict for new version
    query_dict = {}
    avoid_countries = set()
    avoid_firs = set()
    for parameter in url_parameters:
        current_parameter = parameter.split('=')
        converted_parameter = convert_parameter(current_parameter[0], current_parameter[1])
        if converted_parameter is not None:
            for query_key in converted_parameter.keys():
                if query_key == 'avoid_countries':
                    avoid_countries.add(converted_parameter.get(query_key))
                elif query_key == 'avoid_firs':
                    avoid_firs.add(converted_parameter.get(query_key))
                else:
                    query_dict.update(converted_parameter)
    if len(avoid_countries) > 0:
        query_dict.update({'avoid_countries': list(avoid_countries)})
    if len(avoid_firs) > 0:
        query_dict.update({'avoid_firs': list(avoid_countries)})
    return query_dict


def convert_parameter(name: str, value: str) -> dict|None:
    same_name = {
        'departure_airport',
        'arrival_airport',
        'pax'
    }
    if name in same_name:
        name_v2 = name
    elif name == 'departure_date_utc':
        name_v2 = 'departure_datetime'
    elif name == 'aircraft_profile':
        name_v2 = 'aircraft'
    elif name == 'airway':
        bool_value = True if value == 'true' else False
        return {
            'airway_time': bool_value,
            'airway_distance': bool_value,
            'airway_fuel': bool_value
        }
    elif name == 'weather_impact':
        bool_value = True if value == 'true' else False
        return {
            'airway_time_weather_impacted': bool_value,
            'airway_fuel_weather_impacted': bool_value
        }
    elif name == 'fields':
        if value == 'great_circle_route':
            return {
                'great_circle_route': True
            }
        elif value == 'airway_route':
            return {
                'airway_route': True
            } 
    elif 'avoid_countries' in name:
        name_v2 = 'avoid_countries'
    elif 'avoid_firs' in name:
        name_v2 = 'avoid_firs'
    else:
        return None

    if name == 'pax':
        value = int(value)

    return {
        name_v2: urllib.parse.unquote_plus(value) if isinstance(value, str) else value
    }


async def test_api_queries(queries: list) -> list:
    async with aiohttp.ClientSession(headers=HEADERS, trust_env=True) as session:
        tasks = []
        for query in alive_it(queries):
            tasks.append(asyncio.ensure_future(test_api_query(session, query)))
        
        return await asyncio.gather(*tasks)


async def test_api_query(session, query: dict) -> set:
    url = 'https://frc.aviapages.com:443/flight_calculator/'
    start_time = time.time()
    async with session.post(url, json=query, ssl=SSL_CONTEXT) as request:
        elapsed_time = (time.time() - start_time) * 1000
        error_codes = set()
        error_messages = set()
        warning_codes = set()
        warning_messages = set()
        if request.status == 200:
            request_json = await request.json()
            if 'errors' in request_json.keys():
                for error in request_json.get('errors'):
                    error_codes.add(error.get('code'))
                    error_messages.add(error.get('message'))
            if 'warnings' in request_json.keys():
                for warnings in request_json.get('warnings'):
                    for warning in warnings:
                        warning_codes.add(warning.get('code'))
                        warning_messages.add(warning.get('message'))
        return {
            'request_body': query,
            'elapsed_time': elapsed_time,
            'status_code': request.status,
            'error_codes': error_codes,
            'error_messages': error_messages,
            'warning_codes': warning_codes,
            'warning_messages': warning_messages
        }


if __name__ == '__main__':
    main()
    