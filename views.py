from django.urls import reverse_lazy
from django.views.generic import FormView

import requests
import json
from coursera_house.settings import SMART_HOME_API_URL, SMART_HOME_ACCESS_TOKEN
from django.shortcuts import render

from .models import Setting
from .form import ControllerForm

from jsonschema import validate
from jsonschema.exceptions import ValidationError
from django.http import HttpResponse, JsonResponse


class ControllerView(FormView):

    # form_class = ControllerForm
    success_url = reverse_lazy('form')

    def get(self, request):
        r = requests.get(url=SMART_HOME_API_URL, headers={'Authorization': 'Bearer {}'.format(SMART_HOME_ACCESS_TOKEN)})
        if r.status_code != 200:
            return render(request, 'core/error.html', context={'error': '502'}, status=502)

        context = {}
        # getting settings from base
        temp_bedroom = Setting.objects.get(controller_name="bedroom_target_temperature").value
        temp_water = Setting.objects.get(controller_name="hot_water_target_temperature").value
        # creating data dictionary
        data = {}
        info = json.loads(r.text)['data']
        for item in info:
            data[item['name']] = item['value']
        # form init fill
        init_form_data = {
            'bedroom_target_temperature': temp_bedroom,
            'hot_water_target_temperature': temp_water,
            'bedroom_light': data['bedroom_light'],
            'bathroom_light': data['bathroom_light']
        }
        form = ControllerForm(init_form_data)
        context['form'] = form
        context['data'] = data
        return render(request, 'core/control.html', context)

    def post(self, request):
        try:
            # validation
            doc = {}
            doc['bedroom_target_temperature'] = int(request.POST['bedroom_target_temperature'])
            doc['hot_water_target_temperature'] = int(request.POST['hot_water_target_temperature'])
            if 'bedroom_light' in request.POST:
                doc['bedroom_light'] =request.POST['bedroom_light']
            if 'bathroom_light' in request.POST:
                doc['bathroom_light'] =request.POST['bathroom_light']
            validate(doc, REVIEW_SCHEMA_1)

            temp_bedroom_set = Setting.objects.get(controller_name="bedroom_target_temperature")
            if temp_bedroom_set.value != request.POST['bedroom_target_temperature']:
                temp_bedroom_set.value = request.POST['bedroom_target_temperature']
                temp_bedroom_set.save()

            temp_water_set = Setting.objects.get(controller_name="hot_water_target_temperature")
            if temp_water_set.value != request.POST['hot_water_target_temperature']:
                temp_water_set.value = request.POST['hot_water_target_temperature']
                temp_water_set.save()

            r = requests.get(url=SMART_HOME_API_URL,
                             headers={'Authorization': 'Bearer {}'.format(SMART_HOME_ACCESS_TOKEN)})
            if r.status_code != 200:
                return render(request, 'core/error.html', context={'error': '502'}, status=502)
            data = {}
            info = json.loads(r.text)['data']
            for item in info:
                data[item['name']] = item['value']

            '''
            with open('POST_from_api.txt', 'a') as f:
                json.dump(data, f)
                f.write('\n')
            '''

            must_change = list()

            if ('bedroom_light' in request.POST) and (not data['smoke_detector']):
                bed_val = "true"
                bed_val_flag = True
            else:
                bed_val = 'false'
                bed_val_flag = False

            if ('bathroom_light' in request.POST) and (not data['smoke_detector']):
                bath_val = "true"
                bath_val_flag = True
            else:
                bath_val = 'false'
                bath_val_flag = False

            if (bed_val_flag != data['bedroom_light']) and (not data['smoke_detector']):
                must_change.append({
                    "name": "bedroom_light",
                    "value": bed_val
                })
                data['bedroom_light'] = bed_val_flag

            if (bath_val_flag != data['bathroom_light']) and (not data['smoke_detector']):
                must_change.append({
                    "name": "bathroom_light",
                    "value": bath_val
                })
                data['bathroom_light'] = bath_val_flag

            if must_change:
                data_json = json.dumps({"controllers": must_change})
                r = requests.post(url=SMART_HOME_API_URL,
                                  headers={'Authorization': 'Bearer {}'.format(SMART_HOME_ACCESS_TOKEN)},
                                  data=data_json)
            '''
            with open('POST_must_change.txt', 'a') as f:
                json.dump(must_change, f)
                f.write('\n')
            '''
            init_form_data = {
                'bedroom_target_temperature': temp_bedroom_set.value,
                'hot_water_target_temperature': temp_water_set.value,
                'bedroom_light': data['bedroom_light'],
                'bathroom_light': data['bathroom_light']
            }
            form = ControllerForm(init_form_data)
            context = dict()
            context['form'] = form
            context['data'] = data

            return render(request, 'core/control.html', context)

        except ValueError:
            return JsonResponse({'errors': 'Invalid DATA'}, status='400')
        except ValidationError as exc:
            return JsonResponse({'errors': 'here: {}'.format(exc.message)}, status='400')


REVIEW_SCHEMA_1 = {
    '$schema': 'http://json-schema.org/schema#',
    'type': 'object',
    'properties': {
        'bedroom_target_temperature': {
            'type': 'integer',
            'minLength': 16,
            'maxLength': 50,
        },
        'hot_water_target_temperature': {
            'type': 'integer',
            'minLength': 24,
            'maxLength': 90,
        },
        'bedroom_light': {
            'type': 'string',
            'enum': ['on']
        },
        'bathroom_light': {
            'type': 'string',
            'enum': ['on']
        },
    },
    'required': ['bedroom_target_temperature', 'hot_water_target_temperature']
}
