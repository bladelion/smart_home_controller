from __future__ import absolute_import, unicode_literals
from celery import task
import requests
import json
from coursera_house.settings import SMART_HOME_ACCESS_TOKEN, SMART_HOME_API_URL, EMAIL_RECEPIENT
from .models import Setting
from django.http import HttpResponse

from django.core.mail import send_mail


@task()
def smart_home_manager():

    # getting controller state
    data = get_states()

    # list of necessary changes
    must_change = list()

    # write_to_file('from_api.txt', data)
    changes = list()

    # checking conditions
    # 6 *************************************************** smoke detector ************************************
    if data['smoke_detector']:
        if (data['air_conditioner']) and ('air_conditioner' not in changes):
            must_change.append({"name": "air_conditioner", "value": "false"})
            data['air_conditioner'] = False
            changes.append('air_conditioner')
        if (data['bedroom_light']) and ('bedroom_light' not in changes):
            must_change.append({"name": "bedroom_light", "value": "false"})
            data['bedroom_light'] = False
            changes.append('bedroom_light')
        if (data['bathroom_light']) and ('bathroom_light' not in changes):
            must_change.append({"name": "bathroom_light", "value": "false"})
            data['bathroom_light'] = False
            changes.append('bathroom_light')
        if (data['boiler']) and ('boiler' not in changes):
            must_change.append({"name": "boiler", "value": "false"})
            data['boiler'] = False
            changes.append('boiler')
        if (data['washing_machine'] != 'off') and ('washing_machine' not in changes):
            must_change.append({"name": "washing_machine", "value": "off"})
            data['washing_machine'] = "off"
            changes.append('washing_machine')
    # *********************************************************************************************************

    # 1 *************************************************** leak detector ************************************
    if data['leak_detector']:
        if (data['cold_water']) and ('cold_water' not in changes):
            must_change.append({"name": "cold_water", "value": "false"})
            data['cold_water'] = False
            changes.append('cold_water')
        if (data['hot_water']) and ('hot_water' not in changes):
            must_change.append({"name": "hot_water", "value": "false"})
            data['hot_water'] = False
            changes.append('hot_water')
        rmes = send_mail('coursera_house', 'leak detected!', 'example@examle.com',
                         [EMAIL_RECEPIENT], fail_silently=True)
    # *********************************************************************************************************

    # 2 *************************************************** is water cold? ************************************
    if not data['cold_water']:
        if (data['boiler']) and ('boiler' not in changes):
            must_change.append({"name": "boiler", "value": "false"})
            data['boiler'] = False
            changes.append('boiler')
        if (data['washing_machine'] != 'off') and ('washing_machine' not in changes):
            must_change.append({"name": "washing_machine", "value": "off"})
            data['washing_machine'] = "off"
            changes.append('washing_machine')
    # *********************************************************************************************************

    # 3 *************************************************** boiler temperature ********************************
    temp_water = Setting.objects.get(controller_name="hot_water_target_temperature").value
    if data['cold_water'] and (not data['leak_detector']) and (not data['smoke_detector']):
        if data['boiler_temperature'] < (temp_water - 0.1 * temp_water):
            if (not data['boiler']) and (data['boiler_temperature']) and ('boiler' not in changes):
                must_change.append({"name": "boiler", "value": "true"})
                data['boiler'] = True
                changes.append('boiler')
        elif (data['boiler_temperature'] >= (temp_water + 0.1 * temp_water)) and data['boiler_temperature']:
            if (data['boiler']) and ('boiler' not in changes):
                must_change.append({"name": "boiler", "value": "false"})
                data['boiler'] = False
                changes.append('boiler')
    # *********************************************************************************************************

    # 4 and 5 ************************************************** auto curtains ********************************
    if data['curtains'] != 'slightly_open':
        if (data['outdoor_light'] < 50) and (not data['bedroom_light']):
            if data['curtains'] != 'open':
                must_change.append({"name": "curtains", "value": "open"})
                data['curtains'] = 'open'
        elif (data['outdoor_light'] > 50) or (data['bedroom_light']):
            if data['curtains'] != 'close':
                must_change.append({"name": "curtains", "value": "close"})
                data['curtains'] = "close"
    # *********************************************************************************************************

    # 7 ************************************************** bedroom temperature ********************************
    temp_bedroom = Setting.objects.get(controller_name="bedroom_target_temperature").value
    if not data['smoke_detector']:
        if data['bedroom_temperature'] > (temp_bedroom + 0.1 * temp_bedroom):
            if (not data['air_conditioner']) and ('air_conditioner' not in must_change):
                must_change.append({"name": "air_conditioner", "value": "true"})
                data['air_conditioner'] = True
        elif data['bedroom_temperature'] < (temp_bedroom - 0.1 * temp_bedroom):
            if (data['air_conditioner']) and ('air_conditioner' not in must_change):
                must_change.append({"name": "air_conditioner", "value": "false"})
                data['air_conditioner'] = False
    # *********************************************************************************************************

    if must_change:
        data_json = json.dumps({"controllers": must_change})
        r = requests.post(url=SMART_HOME_API_URL,
                          headers={'Authorization': 'Bearer {}'.format(SMART_HOME_ACCESS_TOKEN)},
                          data=data_json)

    # write_to_file('must_change.txt', must_change)


def get_states():
    r = requests.get(url=SMART_HOME_API_URL, headers={'Authorization': 'Bearer {}'.format(SMART_HOME_ACCESS_TOKEN)})
    data = {}
    info = json.loads(r.text)['data']
    for item in info:
        data[item['name']] = item['value']
    return data


def write_to_file(filename, data):
    with open(filename, 'a') as f:
        json.dump(data, f)
        f.write('\n')
