from influxdb_client import InfluxDBClient
import json
import yaml
import aiohttp
import asyncio
import aiofiles
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from .const import DOMAIN
from homeassistant.core import HomeAssistant, ServiceCall

HA_URL = "http://homeassistant.local:8123"


async def process_trend_data(call: ServiceCall):
    """Handle the service call."""
    geminikey = call.hass.data[DOMAIN].get("ai_key")
    if not geminikey:
        # Handle missing API key
        return

    # Fetch trend data
    trend_data = await get_trend_data(call)

    # Analyze data and generate automation suggestions
    gemini_response = await analyze_home_data(trend_data, geminikey)

    if gemini_response:
        # Save to automations.yaml
        async with aiofiles.open("automations.yaml", "w") as file:
            await file.write(gemini_response)
        
        await async_validate_automations(call)


async def get_trend_data(call: ServiceCall):
    """Query last 7 days of data."""
    influx_url = call.hass.data[DOMAIN].get("influx_url")
    influx_token = call.hass.data[DOMAIN].get("influx_token")
    influx_bucket = call.hass.data[DOMAIN].get("influx_bucket")
    influx_org = call.hass.data[DOMAIN].get("influx_org")

    if not all([influx_url, influx_token, influx_bucket, influx_org]):
        # Handle missing InfluxDB config
        return []

    query = f'''
        from(bucket: "{influx_bucket}")
        |> range(start: -7d)
    '''

    def do_query():
        with InfluxDBClient(url=influx_url, token=influx_token, org=influx_org) as client:
            query_api = client.query_api()
            return query_api.query(org=influx_org, query=query)

    result = await call.hass.async_add_executor_job(do_query)

    history = []
    for table in result:
        for record in table.records:
            history.append(
                {
                    "entity": record.get_field(),
                    "state": record.get_value(),
                    "time": record.get_time(),
                }
            )
    return history


async def analyze_home_data(trend_data, api_key):
    """Analyze trend data and suggest automations using Gemini."""
    prompt = f"""
    Given the following Home Assistant trend data for the past 7 days, suggest automations.

    Data:
    {trend_data}

    Provide suggestions in YAML format that Home Assistant can use directly.
    Automations should focus on:
    - Energy efficiency (lights, HVAC)
    - Security (locks, alarms)
    - User comfort (lighting, heating, reminders)
    - Predictive automations based on usage patterns
    """

    # This is a placeholder for the actual Gemini API call
    # In a real implementation, you would use a library like google-generativeai
    # For example:
    # import google.generativeai as genai
    # genai.configure(api_key=api_key)
    # model = genai.GenerativeModel('gemini-pro')
    # response = await model.generate_content_async(prompt)
    # return response.text
    
    # For now, returning a sample YAML response
    return """
- alias: 'Turn off lights when everyone leaves'
  trigger:
    platform: state
    entity_id: group.all_persons
    to: 'not_home'
  action:
    service: light.turn_off
    entity_id: all
"""


async def async_validate_automations(call: ServiceCall):
    """Validate and reload automations."""
    session = async_get_clientsession(call.hass)
    headers = {
        "Authorization": f"Bearer {call.hass.data[DOMAIN]['ha_token']}",
        "Content-Type": "application/json",
    }

    try:
        async with aiofiles.open("automations.yaml", "r") as file:
            yaml_data = yaml.safe_load(await file.read())
    except (FileNotFoundError, yaml.YAMLError):
        # Handle file not found or invalid YAML
        return

    url = f"{HA_URL}/api/config/core/check_config"
    async with session.post(url, headers=headers) as response:
        if response.status == 200:
            print("✅ Configuration check passed. Reloading automations...")
            reload_url = f"{HA_URL}/api/services/homeassistant/reload_core_config"
            await session.post(reload_url, headers=headers)
        else:
            print("Invalid configuration.")
