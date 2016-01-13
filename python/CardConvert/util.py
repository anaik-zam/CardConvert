import os
import re
import yaml
import inspect
import logging
import multiprocessing
from cards.cards import Cards
from cards.heroes import Heroes
from cards.cardbacks import CardBacks

logger = multiprocessing.get_logger()
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s %(name)-12s %(levelname)-8s %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)


def get_config_path():
    """
    Function to get the path to CardConvert.yaml
    Returns:
        config_path (str): path to the config
    """
    config_path = os.getenv('CARDCONVERT_CONFIG')
    if not config_path:
        current_frame = inspect.currentframe()
        src_file = inspect.getsourcefile(current_frame)
        config_name = 'CardConvert.yaml'
        module_path = re.split('python', src_file)[0]
        config_path = os.path.join(module_path, 'config', config_name)
    return config_path


def load_config(config_path=''):
    """
    Function to load the configuration CardConvert.yaml
    Args:
        config_path (str): path to the config file
    Returns:
        config (dict): the config
    """
    if not config_path:
        config_path = get_config_path()
    handle = file(config_path, 'r')
    config = yaml.load(handle)
    handle.close()
    return config


def get_card_instances(card_types, config, input_path):
    """
    Function to create instances of card types in the input_path
    Args:
        card_types (list): list of card types to search ['cards', 'cardbacks', 'heroes']
        config (dict): configuration
        input_path (str): path to look in
    Returns:
        instances (list): list of created instances
    """
    instances = []
    for card_type in card_types:
        obj = None
        if card_type == 'cards':
            obj = Cards(config)
        if card_type == 'cardbacks':
            obj = CardBacks(config)
        if card_type == 'heroes':
            obj = Heroes(config)
        if obj:
            path = os.path.join(input_path, config['card_types'][obj.card_class]['unity_folder'])
            card_dict = obj.crawl_for_this_card_class(path)
            instances += obj.create_instances(card_dict)
    return instances


def _execute_pool(instance, output_path):
    """
    This function is called by each instance in the process pool
    Args:
        instance (obj): instance to execute
        output_path (str): path to write to
    Returns:
        final output
    """
    return instance.process(output_path)


def execute_pool(card_types, config, input_path, output_path, processes=None):
    """
    This function executes the conversion process in a multiprocessing.pool to run in conversion in parallel
    Args:
        card_types (list): list of card types to search ['cards', 'cardbacks', 'heroes']
        config (dict): configuration
        input_path (str): path to look in
        output_path (str): path to write to
        processes (int): number of process in the pool
    Returns:
        output : final output
    """
    if not processes:
        processes = config['processes']
    instances = get_card_instances(card_types, config, input_path)
    pool = multiprocessing.Pool(processes=processes)
    results = [pool.apply_async(_execute_pool, args=(instance, output_path)) for instance in instances]
    output = [p.get() for p in results]
    return output
