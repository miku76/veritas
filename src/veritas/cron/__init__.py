import functools
from datetime import date

weekday = {'monday': 0,
           'tuesday': 1,
           'wednesday': 2,
           'thursday': 3,
           'friday': 4,
           'saturday': 5,
           'sunday': 6}

def on(day):
    def decorator_on(func):
        @functools.wraps(func)
        def wrapper_on_day(*args, **kwargs):
            days = [day] if not isinstance(day, list) else day
            # create a list of bools; true if weekday matches day else false
            if any([date.today().weekday() == weekday.get(d.lower()) for d in days]):
                return func(*args, **kwargs)
            return None
        return wrapper_on_day
    return decorator_on

