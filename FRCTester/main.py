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
from tqdm.asyncio import tqdm


BASE_DIR = Path(__file__).resolve().parent
REPORTS_PATH = f'{BASE_DIR}/reports'

SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())
HEADERS = {
    'Content-Type': 'application/json',
    'Authorization': f'Token {os.environ.get("API_TOKEN")}'
}

logging.basicConfig(level=logging.INFO)


def main():
    logger = logging.getLogger('FRC TESTER')
    
    logger.info('Start of FRC requests testing...')
    
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
    logger.info(f'Report file created locally at {os.environ.get("LOCAL_PATH")}')

def get_queries() -> list:
    queries = []
    with open(f'{BASE_DIR}/{os.environ.get("FILENAME")}') as file:
        reader = csv.reader(file, delimiter=',')
        for row in alive_it(reader):
            if '/api/v1/flight_calculator' in row[2]:
                query_data_v1 = get_query_data_v1(row[2])
                if query_data_v1 is not None:
                    queries.append(query_data_v1)
                queries.append(get_query_data_v1(row[2]))
            elif '{"url": "/flight_calculator' in row[2]:
                query_data_v2 = get_query_data_v2(row[2])
                if query_data_v2 is not None:
                    queries.append(query_data_v2)

    return queries


def get_query_data_v2(query: str) -> dict|None:
    # Preparation text for processing
    text = query.split('{')
    if len(text) < 3:
        return None
    
    text = text[2].replace('}"}', '')
    text = text.replace('\\n', '')
    text = text.replace('\\', '')
    
    # Getting query parameters
    query_dict = {}
    request_parameters = text.split(',')
    for i in range(len(request_parameters)):
        current_parameter = request_parameters[i].split('":')
        if len(current_parameter) == 2:
            converted_parameter = convert_parameter_v2(current_parameter[0], current_parameter[1])
            query_dict.update(converted_parameter)
        else:
            # Current parameter could be empty
            if len(current_parameter[0].strip()) == 0:
                continue
            # We should find key for current value
            for y in range(i, 0, -1):
                temp_parameter = request_parameters[y].split('":')
                if len(temp_parameter) == 2:
                    # Key was found
                    converted_parameter = convert_parameter_v2(temp_parameter[0], current_parameter[0])
                    # 1 cicle loop
                    for key in converted_parameter.keys():
                        value = converted_parameter.get(key)
                        current_value = query_dict.get(key)
                        if isinstance(value, list):
                            current_value.append(value[0])
                        else:
                            current_value.append(value)
                        query_dict.update({key: current_value})
                    break
    
    return query_dict
        

def convert_parameter_v2(name: str, value: str) -> dict:
    name = name.strip().replace('"', '')
    value = value.strip().replace('"', '')
    if '[]' in name or '[' in value or ']' in value:
        name = name.replace('[]', '')
        value = value.replace('[', '').replace(']', '')
        value_v2 = []
        if len(value) > 0:
            for list_value in value.split(','):
                value_v2.append(list_value.strip())
    elif value == 'true':
        value_v2 = True
    elif value == 'false':
        value_v2 = False
    elif 'pax' in name:
        value_v2 = int(value) if len(value) > 0 else 0
    else:
        value_v2 = value
        
    return {name: value_v2}
    

def get_query_data_v1(query: str) -> dict|None:
    # Getting query parameters
    url = query.split('"')[3]
    url = url.split('?')
    if len(url) < 2:
        return None
    url_query = url[1]
    
    url_parameters = url_query.split('&')
    if len(url_parameters) == 0:
        return None

    # Generating dict for new version
    query_dict = {}
    avoid_countries = set()
    avoid_firs = set()
    for parameter in url_parameters:
        current_parameter = parameter.split('=')
        converted_parameter = convert_parameter_v1(current_parameter[0], current_parameter[1])
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


def convert_parameter_v1(name: str, value: str) -> dict|None:
    name_v2 = name
    same_name = {
        'departure_airport',
        'arrival_airport',
        'pax'
    }
    if name in same_name:
        name_v2 = name.strip()
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
        for query in queries:
            tasks.append(asyncio.ensure_future(test_api_query(session, query)))
        return [
            await f
            for f in tqdm(asyncio.as_completed(tasks), total=len(tasks))
        ]
        
        # return await asyncio.gather(*tasks)


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
    