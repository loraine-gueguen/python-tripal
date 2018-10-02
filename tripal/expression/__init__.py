from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import json
import logging
from collections import OrderedDict

from tripal.client import Client

logging.getLogger("requests").setLevel(logging.CRITICAL)
log = logging.getLogger()


class ExpressionClient(Client):
    """Manage Tripal expressions"""

    def add_expression(self, organism_id, analysis_id, file_path,
                       match_type="uniquename", biomaterial_provider=None, array_design=None, assay_id=None,
                       acquisition_id=None, quantification_id=None, file_extension=None,
                       start_regex=None, stop_regex=None, use_column=False, no_wait=False):
        """
        :type organism_id: str
        :param organism_id: Organism Id

        :type analysis_id: str
        :param analysis_id: Id of the analysis

        :type match_type: str
        :param match_type: Match to features using either name or uniquename. Default to uniquename

        :type file_path: str
        :param file_path: Path to the expression file, or directory containing multiple expression files

        :type biomaterial_provider: str
        :param biomaterial_provider: The contact who provided the biomaterial. (optional, non functional in Tripal2)

        :type array_design: str
        :param array_design: The array design associated with this analysis. This is not required if the experimental data was gathered from next generation sequencing methods. (optional, non functional in Tripal2)

        :type assay_id: str
        :param assay_id: The id of the assay associated with the experiment. (optional, non functional in Tripal2)

        :type acquisition_id: str
        :param acquisition_id: The id of the acquisition associated with the experiment (optional, non functional in Tripal2)

        :type quantification_id: str
        :param quantification_id: The id of the quantification associated with the experiment (optional, non functional in Tripal2)

        :type file_extension: str
        :param file_extension: File extension for the file(s) to be loaded into Chado. Do not include the ".". Not required for matrix files. (optional)

        :type start_regex: str
        :param start_regex: A regular expression to describe the line that occurs before the start of the expression data. If the file has no header, this is not needed. (optional)

        :type stop_regex: str
        :param stop_regex: A regular expression to describe the line that occurs after the end of the expression data. If the file has no footer text, this is not needed. (optional)

        :type use_column: bool
        :param use_column: Set if the expression file is a column file

        :type no_wait: bool
        :param no_wait: Do not wait for job to complete

        :rtype: str
        :return: Loading information
        """

        if use_column:
            file_type = "col"
        else:
            file_type = "mat"

        if file_type == "col" and not file_extension:
            raise Exception("File_extension is required for column files")

        if match_type not in ["uniquename", "name"]:
            raise Exception("match_type should be 'name' or 'uniquename'")

        if match_type == "uniquename":
            match_type = "uniq"

        job_args = [organism_id, analysis_id, biomaterial_provider, array_design, assay_id, acquisition_id, quantification_id, file_path, file_extension, file_type, start_regex, stop_regex, match_type]

        r = self.tripal.job.add_job("Add Expression", 'tripal_analysis_expression', 'tripal_expression_loader', job_args)

        if 'job_id' not in r or not r['job_id']:
            raise Exception("Failed to create job, received %s" % r)

        if no_wait:
            return r
        else:
            return self._run_job_and_wait(r['job_id'])

    def get_biomaterials(self, provider_id="", biomaterial_id="", organism_id="", dbxref_id=""):
        """
        List biomaterials in the database

        :type organism_id: str
        :param organism_id: Limit query to the selected organism

        :type biomaterial_id: str
        :param biomaterial_id: Limit query to the selected biomaterial

        :type provider_id: str
        :param provider_id: Limit query to the selected provider

        :type dbxref_id: str
        :param dbxref_id: Limit query to the selected ref

        :rtype: dict
        :return: Job information
        """
        orgs = self._request('chado/list', {'table': 'biomaterial'})
        if biomaterial_id:
            orgs = [v for v in orgs if v['biomaterial_id'] == str(biomaterial_id)]
        if provider_id:
            orgs = [v for v in orgs if v['biosourceprovider_id'] == str(provider_id)]
        if organism_id:
            orgs = [v for v in orgs if v['taxon_id'] == str(organism_id)]
        if dbxref_id:
            orgs = [v for v in orgs if v['dbxref_id'] == str(dbxref_id)]
        return orgs

    def add_biomaterial(self, organism_id, file_path, file_type, no_wait=False):
        """
        Add a new biomaterial to the database

        :type organism_id: str
        :param organism_id: The id of the associated organism

        :type file_path: str
        :param file_path: The path to the biomaterial file

        :type file_type: str
        :param file_type: The type of the biomaterial file (xml, tsv or csv)

        :type no_wait: bool
        :param no_wait: Do not wait for job to complete

        :rtype: dict
        :return: Job information
        """

        if file_type not in ['xml', 'tsv', 'csv']:
            raise Exception("File format must be one of ['xml', 'tsv', 'csv']")

        if file_type == "xml":
            job_args = [file_path, organism_id]
            callback = 'xml_biomaterial_parser'

        else:
            job_args = [file_path, organism_id, file_type]
            callback = 'flat_biomaterial_parser'

        r = self.tripal.job.add_job("Add Biomaterial", 'tripal_analysis_expression', callback, job_args)

        if 'job_id' not in r or not r['job_id']:
            raise Exception("Failed to create job, received %s" % r)

        if no_wait:
            return r
        else:
            return self._run_job_and_wait(r['job_id'])

    def delete_biomaterials(self, names=[], organism_id="", analysis_id="", job_name="", no_wait=False):
        """
        Delete some biomaterials

        :type names: str
        :param names: JSON list of biomaterial names to delete. (optional)

        :type organism_id: str
        :param organism_id: Organism id from which to delete biomaterials (optional)

        :type analysis_id: str
        :param analysis_id: Analysis id from which to delete biomaterials (optional)

        :type no_wait: bool
        :param no_wait: Return immediately without waiting for job completion

        :type job_name: str
        :param job_name: Name of the job (optional)

        :rtype: str
        :return: status
        """

        if not isinstance(names, list) and not isinstance(names, dict):
            names = json.loads(names)

        # Convert to space separated string
        names = " ".join(names)

        if(not (names or organism_id or analysis_id)):
            raise Exception("Please provide either a list of biomaterial names, an analysis id, or an organism id")

        if not job_name:
            job_name = 'Delete Biomaterials'

        job_args = OrderedDict()
        job_args['biomaterial_names'] = names
        job_args['organism_id'] = organism_id
        job_args['analysis_id'] = analysis_id

        r = self.tripal.job.add_job(job_name, 'tripal_biomaterial', 'tripal_biomaterial_delete_biomaterials', job_args)
        if 'job_id' not in r or not r['job_id']:
            raise Exception("Failed to create job, received %s" % r)

        if no_wait:
            return r
        else:
            return self._run_job_and_wait(r['job_id'])

    def sync_biomaterials(self, ids=[], max_sync='', job_name=None, no_wait=False):
        """
        Synchronize some biomaterials

        :type ids: str
        :param ids: JSON list of ids of biomaterials to be synced (default: all)

        :type max_sync: str
        :param max_sync: Maximum number of features to sync (default: all)

        :type job_name: str
        :param job_name: Name of the job

        :type no_wait: bool
        :param no_wait: Return immediately without waiting for job completion

        :rtype: str
        :return: status
        """

        if not job_name:
            job_name = 'Sync Biomaterials'

        if not isinstance(ids, list) and not isinstance(ids, dict):
            ids = json.loads(ids)

        if self.tripal.version == 3:
            raise NotImplementedError("Not yet possible in Tripal 3")

        else:
            job_args = OrderedDict()
            job_args['base_table'] = 'biomaterial'
            job_args['max_sync'] = max_sync
            job_args['organism_id'] = ''
            job_args['types'] = []
            job_args['ids'] = ids
            job_args['linking_table'] = 'chado_biomaterial'
            job_args['node_type'] = 'chado_biomaterial'

            r = self.tripal.job.add_job(job_name, 'chado_biomaterial', 'chado_node_sync_records', job_args)
            if 'job_id' not in r or not r['job_id']:
                raise Exception("Failed to create job, received %s" % r)

        if no_wait:
            return r
        else:
            return self._run_job_and_wait(r['job_id'])