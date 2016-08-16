import os
import urllib

from abc import ABCMeta
from luigi import Task, Parameter, WrapperTask, LocalTarget

from tasks.util import (DownloadUnzipTask, shell, Shp2TempTableTask,
                        ColumnsTask, TableTask, TempTableTask, classpath,
                        underscore_slugify)
from tasks.meta import GEOM_REF, OBSColumn, current_session
# from tasks.mx.inegi_columns import DemographicColumns
from tasks.tags import SectionTags, SubsectionTags, UnitTags

from collections import OrderedDict
from geo import GEOGRAPHY_CODES
from util import StatCanParser


SURVEYS = (
    'census',
    'nhs',
)

SURVEY_CODES = {
    'census': '98-316-XWE2011001',
    'nhs': '99-004-XWE2011001',
}

SURVEY_URLS = {
    'census': 'census-recensement',
    'nhs': 'nhs-enm',
}

URL = 'http://www12.statcan.gc.ca/{survey_url}/2011/dp-pd/prof/details/download-telecharger/comprehensive/comp_download.cfm?CTLG={survey_code}&FMT=CSV{geo_code}'


class BaseParams:
    __metaclass__ = ABCMeta

    resolution = Parameter(default='pr_')
    survey = Parameter(default='census')


class DownloadData(BaseParams, DownloadUnzipTask):
    def download(self):
        urllib.urlretrieve(url=URL.format(
                           survey_url=SURVEY_URLS[self.survey],
                           survey_code=SURVEY_CODES[self.survey],
                           geo_code=GEOGRAPHY_CODES[self.resolution],
                           ),
                           filename=self.output().path + '.zip')


class SplitAndTransposeData(BaseParams, Task):
    def requires(self):
        return DownloadData(resolution=self.resolution, survey=self.survey)

    def run(self):
        infiles = shell('ls {input}/*[0-9].CSV'.format(
            input=self.input().path
        ))
        in_csv_files = infiles.strip().split('\n')
        os.makedirs(self.output().path)
        # print in_csv_files
        StatCanParser().parse_csv_to_files(in_csv_files, self.output().path)

    def output(self):
        return LocalTarget(os.path.join('tmp', classpath(self), self.task_id))

# class DownloadData(BaseParams, Task):

#     def run(self):
#         self.output().makedirs()
#         urllib.urlretrieve(url=URL.format(
#                            survey_url=SURVEY_URLS[self.survey],
#                            survey_code=SURVEY_CODES[self.survey],
#                            geo_code=GEOGRAPHY_CODES[self.resolution],
#                            ),
#                            filename=self.output().path)

#     def output(self):
#         return LocalTarget(os.path.join('tmp', classpath(self),
#                                         SURVEY_CODES[self.survey] + '-' + str(GEOGRAPHY_CODES[self.resolution]) + '.zip'))


# class UnzipData(BaseParams, Task):
#     def requires(self):
#         return DownloadData(resolution=self.resolution, survey=self.survey)

#     def run(self):
#         cmd = 'unzip -o {input} -d {output_dir}'.format(
#             input=self.input().path,
#             output_dir=self.input().path.replace('.zip', ''))
#         shell(cmd)

#     def output(self):
#         path, folder = os.path.split(self.input().path)
#         folder = folder.replace('.zip', '')
#         csv_file = folder + '.CSV'
#         return LocalTarget(os.path.join(path, folder, csv_file))
