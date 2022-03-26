import unittest
import main
import asyncio


class MainTest(unittest.TestCase):
    def test_get_query_data(self):
        query = '{"url": "/api/v1/flight_calculator/?departure_airport=PHKO&arrival_airport=KSFO&pax=2&aircraft_profile=Gulfstream%20G450&departure_date_utc=2022-3-21%2019:00&weather_impact=true&airway=true", "token": null}'
        answer = {
            'departure_airport': 'PHKO',
            'arrival_airport': 'KSFO',
            'pax': 2,
            'aircraft': 'Gulfstream G450',
            'departure_datetime': '2022-3-21 19:00',
            'airway_time': True,
            'airway_distance': True,
            'airway_fuel': True,
            'airway_time_weather_impacted': True,
            'airway_fuel_weather_impacted': True
        }
        self.assertEqual(main.get_query_data(query), answer)
        query = '{"url": "/api/v1/flight_calculator/?departure_airport=PHKO&arrival_airport=KSFO&pax=2&aircraft_profile=Gulfstream%20G450&departure_date_utc=2022-3-21%2019:00&weather_impact=false&airway=false", "token": null}'
        answer = {
            'departure_airport': 'PHKO',
            'arrival_airport': 'KSFO',
            'pax': 2,
            'aircraft': 'Gulfstream G450',
            'departure_datetime': '2022-3-21 19:00',
            'airway_time': False,
            'airway_distance': False,
            'airway_fuel': False,
            'airway_time_weather_impacted': False,
            'airway_fuel_weather_impacted': False
        }
        self.assertEqual(main.get_query_data(query), answer)
    
    def test_api_queries_correct(self):
        queries = [{
            'departure_airport': 'PHKO',
            'arrival_airport': 'KSFO',
            'pax': 2,
            'aircraft': 'Gulfstream G450',
            'departure_datetime': '2022-3-21 19:00',
            'airway_time': True,
            'airway_distance': True,
            'airway_fuel': True,
            'airway_time_weather_impacted': True,
            'airway_fuel_weather_impacted': True
        }]
        results = asyncio.run(main.test_api_queries(queries))
        self.assertGreater(len(results), 0)
        result = results[0]
        self.assertEqual(result.get('request_body'), queries[0])
        self.assertGreater(result.get('elapsed_time'), 0)
        self.assertIsInstance(result.get('status_code'), int)
        self.assertEqual(len(result.get('error_codes')), 0)
        self.assertEqual(len(result.get('error_messages')), 0)
        self.assertEqual(len(result.get('warning_codes')), 0)
        self.assertEqual(len(result.get('warning_messages')), 0)
    
    def test_api_queries_incorrect(self):
        queries = [{
            'departure_airport': 'PHKO',
            'arrival_airport': 'KSFO',
            'pax': 2,
            'aircraft': 'random',
            'departure_datetime': '2022-3-21 19:00',
            'airway_time': True,
            'airway_distance': True,
            'airway_fuel': True,
            'airway_time_weather_impacted': True,
            'airway_fuel_weather_impacted': True
        }]
        results = asyncio.run(main.test_api_queries(queries))
        self.assertGreater(len(results), 0)
        result = results[0]
        self.assertEqual(result.get('request_body'), queries[0])
        self.assertGreater(result.get('elapsed_time'), 0)
        self.assertIsInstance(result.get('status_code'), int)
        self.assertEqual(len(result.get('error_codes')), 2)
        self.assertEqual(len(result.get('error_messages')), 2)
        self.assertEqual(len(result.get('warning_codes')), 0)
        self.assertEqual(len(result.get('warning_messages')), 0)
        queries = [{
            'departure_airport': 'LUKK',
            'arrival_airport': 'UUWW',
            'aircraft_max_fuel': 1200,
            'pax': 2,
            'aircraft': 'Cessna Citation Sovereign',
            'departure_datetime': '2022-3-21 19:00',
            'airway_time': True,
            'airway_distance': True,
            'airway_fuel': True,
            'airway_time_weather_impacted': True,
            'airway_fuel_weather_impacted': True
        }]
        results = asyncio.run(main.test_api_queries(queries))
        self.assertGreater(len(results), 0)
        result = results[0]
        self.assertEqual(result.get('request_body'), queries[0])
        self.assertGreater(result.get('elapsed_time'), 0)
        self.assertIsInstance(result.get('status_code'), int)
        self.assertEqual(len(result.get('error_codes')), 0)
        self.assertEqual(len(result.get('error_messages')), 0)
        self.assertEqual(len(result.get('warning_codes')), 1)
        self.assertEqual(len(result.get('warning_messages')), 1)
    
    def test_convert_parameter(self):
        parameter_name = 'departure_airport'
        parameter_value = 'ABC'
        answer = {'departure_airport': 'ABC'}
        self.assertEqual(main.convert_parameter(parameter_name, parameter_value), answer)
        
        parameter_name = 'departure_date_utc'
        parameter_value = '2022-03-01%2018:15'
        answer = {'departure_datetime': '2022-03-01 18:15'}
        self.assertEqual(main.convert_parameter(parameter_name, parameter_value), answer)
        
        parameter_name = ''
        parameter_value = ''
        answer = None
        self.assertEqual(main.convert_parameter(parameter_name, parameter_value), answer)
        
        parameter_name = 'pax'
        parameter_value = '3'
        answer = {'pax': 3}
        self.assertEqual(main.convert_parameter(parameter_name, parameter_value), answer)
        
        parameter_name = 'aircraft_profile'
        parameter_value = 'my_aircraft'
        answer = {'aircraft': 'my_aircraft'}
        self.assertEqual(main.convert_parameter(parameter_name, parameter_value), answer)

        parameter_name = 'airway'
        parameter_value = 'true'
        answer = {'airway_time': True, 'airway_distance': True, 'airway_fuel': True}
        self.assertEqual(main.convert_parameter(parameter_name, parameter_value), answer)

        parameter_name = 'weather_impact'
        parameter_value = 'false'
        answer = {'airway_time_weather_impacted': False, 'airway_fuel_weather_impacted': False}
        self.assertEqual(main.convert_parameter(parameter_name, parameter_value), answer)

        parameter_name = 'fields'
        parameter_value = 'great_circle_route'
        answer = {'great_circle_route': True}
        self.assertEqual(main.convert_parameter(parameter_name, parameter_value), answer)
        
        parameter_name = 'fields'
        parameter_value = 'airway_route'
        answer = {'airway_route': True}
        self.assertEqual(main.convert_parameter(parameter_name, parameter_value), answer)
        
        parameter_name = 'avoid_countries[]'
        parameter_value = 'Ukraine'
        answer = {'avoid_countries': 'Ukraine'}
        self.assertEqual(main.convert_parameter(parameter_name, parameter_value), answer)
        
        parameter_name = 'avoid_firs[]'
        parameter_value = 'UKSD'
        answer = {'avoid_firs': 'UKSD'}
        self.assertEqual(main.convert_parameter(parameter_name, parameter_value), answer)
            
if __name__ == '__main__':
    unittest.main()
