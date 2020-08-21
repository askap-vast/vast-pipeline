import logging
import pandas as pd
from itertools import islice
from django.db import transaction


logger = logging.getLogger(__name__)


@transaction.atomic
def bulk_upload_model(objs, djmodel, batch_size=10_000):
    '''
    bulk upload a pandas series of django models to db
    objs: pandas.Series
    djmodel: django.model
    '''
    size = objs.size
    objs = objs.values.tolist()

    for idx in range(0, size, batch_size):
        out_bulk = djmodel.objects.bulk_create(
            objs[idx : idx + batch_size],
            batch_size
        )
        logger.info('Bulk created #%i %s', len(out_bulk), djmodel.__name__)
