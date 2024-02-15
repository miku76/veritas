from loguru import logger

# veritas
from veritas.devicemanagement import scrapli as dm
from veritas.onboarding import plugins


@plugins.config_and_facts('ios')
def get_device_config_and_facts(device_ip, device_defaults, profile, tcp_port=22, scrapli_loglevel='none'):

    device_config = None
    device_facts = {}
    conn = dm.Devicemanagement(
        ip=device_ip,
        platform=device_defaults.get('platform','ios'),
        manufacturer=device_defaults.get('manufacturer','cisco'),
        username=profile.username,
        password=profile.password,
        port=tcp_port,
        scrapli_loglevel=scrapli_loglevel)

    # retrieve facts like fqdn, model and serialnumber
    logger.debug('now gathering facts')
    device_facts = conn.get_facts()

    if device_facts is None:
        logger.error('got no facts; skipping device')
        if conn:
            conn.close()
        return None, None
    device_facts['args.device'] = device_ip

    # retrieve device config
    logger.debug("getting running-config")
    try:
        device_config = conn.get_config("running-config")
    except Exception as exc:
        logger.error(f'failed to receive device config from {device_ip}; got exception {exc}', exc_info=True)
        return None, None
    if device_config is None:
        logger.error(f'failed to retrieve device config from {device_ip}')
        conn.close()
        return None, None
    conn.close()

    return device_config, device_facts
