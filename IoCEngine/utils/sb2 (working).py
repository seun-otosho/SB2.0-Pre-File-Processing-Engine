#!/usr/bin/python3
# -*- coding: utf-8 -*-


import inspect
import multiprocessing as mp
import numpy as np
import os
import pandas as pd
import re
import time

from collections import OrderedDict
from datetime import datetime

from IoCEngine import xtrcxn_area
from IoCEngine.celeryio import app
from IoCEngine.commons import get_logger, mk_dir, right_now, std_out
from IoCEngine.utils.data_modes import iff
from IoCEngine.utils.file import DataBatchProcess, DataFiles, pym_db, SB2FileInfo
from IoCEngine.models import CtgryCode, DataProvider

a, b, c = 1, 2, 3


def var_name(var):
    callers_local_vars = inspect.currentframe().f_back.f_locals.items()
    return [var_name for var_name, var_val in callers_local_vars if var_val is var][0]


# print(var_name(b))


def clean_a_line(df_row):
    df_str = '|'.join(str(c) for c in df_row.tolist())
    df_str = re.sub('\s+', ' ', df_str).strip().replace('|-|', '||').replace('|NULL|', '||').replace(
        '|NIL|', '||').replace('|nil|', '||').replace('None', '').replace('…', '')
    df_str = df_str.replace('.0|', '|') if '.0|' in df_str else df_str
    return df_str


def dp_meta_data(dp_code_name=None):
    if dp_code_name and dp_code_name.isalpha():
        data_prvdr = DataProvider.query.filter_by(code_name=dp_code_name).first()
        return {
            data_prvdr.code_name: (
                data_prvdr.dpid, data_prvdr.sbmxn_pt, data_prvdr.ctgry, data_prvdr.day_first)
        }
    if dp_code_name and dp_code_name.isalnum() and not dp_code_name.isalpha():
        data_prvdr = DataProvider.query.filter_by(dpid=dp_code_name).first()
        return {
            data_prvdr.code_name: (
                data_prvdr.dpid, data_prvdr.sbmxn_pt, data_prvdr.ctgry, data_prvdr.day_first)
        }
    if not dp_code_name:
        data_prvdrs = DataProvider.query.all()
        return {
            data_prvdr.code_name: (
                data_prvdr.dpid, data_prvdr.sbmxn_pt, data_prvdr.ctgry, data_prvdr.day_first) for
            data_prvdr in data_prvdrs
        }


def sb2ctgry_file_type_codes(code_name=None):
    if code_name:
        ctgry_code = CtgryCode.query.filter_by(code_name=code_name).first()
        return {ctgry_code.code_name: (ctgry_code.header_code, ctgry_code.file_type_code)}
    else:
        ctgry_codes = DataProvider.query.all()
        return {ctgry_code.code_name: (ctgry_code.header_code, ctgry_code.file_type_code) for ctgry_code in ctgry_codes}


def fix_fac_missing(crdt_data, meta_data):
    crdt_data.insert(0, 'prev_dpid', '')
    crdt_data.insert(0, 'dpid', meta_data['dpid'])


def syndidata(crdt_data, sbjt_data, meta_data, dp_meta, datCat, hdr, sb2file):
    mdjlog, dpid, syndicaxn_complt = get_logger(meta_data['dp_name']), meta_data['dpid'], False
    dp_name, syndi_data_list = meta_data['dp_name'].split('_')[0].lower(), []
    institution_cat, submxn_pt = dp_meta[dp_name][2], dp_meta[dp_name][1]
    file_dtls = DataFiles.objects(dpid=meta_data['dpid'], status='Loaded').first()  # batch_no=meta_data['batch_no'],
    meta_data.reload()
    # try:
    #     loaded_batch = DataBatchProcess.objects(batch_no=meta_data['batch_no'], dpid=meta_data['dpid'],
    #                                             status='Loaded').first()
    # except:
    #     loaded_batch = DataBatchProcess.objects(dpid=meta_data['dpid'], status='Loaded').first()
    loaded_batch = meta_data
    dp_name = loaded_batch['dp_name']
    cust_id, ac_no, data_list, file = None, None, [], file_dtls['file_name']  # , fac_lines, sub_lines [], [],

    if meta_data['data_type'] == 'combo':
        cust_ds, faci_ds = 'combined_submissions', 'combined_submissions'
        cust_rec_col, faci_rec_col = pym_db[cust_ds], pym_db[faci_ds]
    else:
        cust_ds = 'corporate_submissions' if 'com' in datCat else 'individual_submissions'
        cust_rec_col = pym_db[cust_ds]
        faci_ds = 'facility_submissions'
        faci_rec_col = pym_db[faci_ds]
        sbjt_data.fillna('', inplace=True)
    crdt_data.fillna('', inplace=True)
    try:
        iff_fac_cols, iff_sbjt_cols = None, None
        if loaded_batch['out_mod'] == 'cmb':
            if datCat == 'com':
                fac_sgmnt, sbjt_sgmnt = 'CMCF', 'CMCS'
                iff_sbjt_cols = iff()['cmb']['corp']  # ['comm']
                iff_fac_cols = iff()['cmb']['corpfac']  # ['fac']
            if datCat == 'con':
                fac_sgmnt, sbjt_sgmnt = 'CNCF', 'CNCS'
                iff_sbjt_cols = iff()['cmb']['ndvdl']  # ['cons']
                iff_fac_cols = iff()['cmb']['ndvdlfac']  # ['fac']

        if loaded_batch['out_mod'] == 'mfi' or (
                        loaded_batch['in_mod'] == loaded_batch['out_mod'] and loaded_batch['in_mod'] == 'iff'):
            if datCat in ('com', 'mfcom'):
                fac_sgmnt, sbjt_sgmnt = 'CMMF', 'CMMS'
                iff_sbjt_cols = iff()['mfi']['comm']
            if datCat in ('con', 'mfcon'):
                fac_sgmnt, sbjt_sgmnt = 'CNMF', 'CNMS'
                iff_sbjt_cols = iff()['mfi']['cons']
            iff_fac_cols = iff()['mfi']['fac']

        if loaded_batch['out_mod'] == 'pmi':
            if datCat in ('com', 'mgcom'):
                fac_sgmnt, sbjt_sgmnt = 'MMCF', 'MMCS'
                iff_sbjt_cols = iff()['pmi']['comm']
            if datCat in ('con', 'mgcon'):
                fac_sgmnt, sbjt_sgmnt = 'MNCF', 'MNCS'
                iff_sbjt_cols = iff()['pmi']['cons']
            iff_fac_cols = iff()['pmi']['fac']

        dataCount, idx = 0, 0
        syndi_dir = xtrcxn_area + os.path.sep + meta_data['dp_name'].split('_')[0].upper() + os.path.sep
        mk_dir(syndi_dir)
        # sb2file_handler = open(syndi_dir + sb2file, 'w')
        # sb2file_handler.write(hdr + '\n')
        syndi_data_list.append(hdr)
        for idx, crdt in crdt_data.iterrows():
            try:
                ac_no = crdt['account_no']
                # if not idx % 1000:
                #     std_out(
                #         "@{} Matching credit account {} @NDX#{}".format(datetime.utcnow().strftime('%H:%M:%S'), ac_no,
                #                                                         idx))
                if meta_data['data_type'] == 'combo':
                    subj = crdt
                else:
                    try:
                        subj = sbjt_data[sbjt_data['account_no'] == crdt['account_no']]
                    except:
                        subj = sbjt_data[sbjt_data['cust_id'] == crdt['cust_id']]

                if not subj.empty:
                    try:
                        sbjt_rw = subj.to_dict(orient='record')[0]
                    except:
                        sbjt_rw = subj.to_dict()

                    subj = pd.DataFrame([sbjt_rw], index=None)

                    # if loaded_batch['in_mod'] == 'phed':
                    #     if str(subj['cust_id']).strip().upper() == 'NOMETER':
                    #         subj['cust_id'] = subj['account_no']

                    try:
                        branch_code = '001' if meta_data['data_type'] == 'combo' else sbjt_rw['branch_code']
                        branch_code = str(branch_code)[-4:]
                    except:
                        branch_code = '001'

                    crdt['branch_code'] = branch_code
                    crdt_d = crdt[list(iff_fac_cols)]
                    # crdt_d = pd.DataFrame([new_crdt_rw], index=None)
                    #
                    cust_id = crdt['cust_id'] if 'cust_id' in crdt else sbjt_rw['cust_id']

                    if not idx % 1000:
                        mdjlog.info(
                            "@{} Matching credit account {} . .. with customer ID {} @NDX#{}".format(
                                datetime.utcnow().strftime('%H:%M:%S'), ac_no, cust_id, idx))

                    subj['account_no'] = crdt.account_no if 'account_no' not in subj else subj.account_no
                    subj['account_no'] = subj['account_no'].apply(lambda x: x if isinstance(x, str) else str(int(x)))
                    sbjt0d = {k: subj[k][0] if k in subj else '' for k in iff_sbjt_cols}

                    # try:
                    #     if sbjt0d['bvn'] and isinstance(sbjt0d['bvn'], float):
                    #         sbjt0d[bvn] = sbjt0d[bvn].apply(lambda x: str(int(x)) if isinstance(x, float) else x )
                    # except Exception as e:
                    #     mdjlog.error("{}".format(e))

                    sbjt1d = pd.DataFrame([sbjt0d], index=None)
                    sbjt_d = sbjt1d[list(iff_sbjt_cols)]

                    crdt_d.fillna(value='', inplace=True)
                    sbjt_d.fillna(value='', inplace=True)

                    a_fac_line = clean_a_line(crdt_d)
                    a_fac_line = fac_sgmnt + '|' + meta_data['dpid'] + '||' + a_fac_line

                    if str(ac_no).replace('_', '').replace('-', '').strip() != '':

                        if not str(ac_no).replace('_', '').strip().isalpha() \
                                and not str(ac_no).replace('-', '').strip().isalpha() \
                                and not str(ac_no).replace(' ', '').strip().isalpha():

                            try:
                                cust_id = subj.cust_id.values[0]
                            except Exception as e:
                                try:
                                    cust_id = subj.cust_id
                                except Exception as e:
                                    mdjlog.error("{}".format(e))

                            # sb2file_handler.write(a_fac_line + '\n')
                            # if loaded_batch['in_mod'] in ('cmb', 'fandl', 'iff', 'mfi', 'pmi',):
                            # cycle_ver = loaded_batch['cycle_ver']
                            # try:
                            #     faci_rec_col.update(
                            #         {"dpid": loaded_batch['dpid'], "account_no": ac_no, "cycle_ver": cycle_ver},
                            #         {'$set': {'status': 'Syndicated'}}
                            #     )
                            # except Exception as e:
                            #     mdjlog.error("{} | facility record: {}".format(e, crdt))

                            a_sbjt_line = '|'.join(str(c) for c in sbjt_d.iloc[0].tolist())  #
                            a_sbjt_line = re.sub('\s+', ' ', a_sbjt_line).replace("|'", '|').strip().replace('…', ' ')
                            a_sbjt_line = sbjt_sgmnt + '|' + meta_data['dpid'] + '|' + a_sbjt_line
                            # sb2file_handler.write(a_sbjt_line + '\n')
                            syndi_data_list.append(a_fac_line)
                            syndi_data_list.append(a_sbjt_line)
                            # if loaded_batch['in_mod'] in ('cmb', 'fandl', 'iff', 'mfi', 'pmi',):  # , upsert=True
                            #     try:
                            #         cust_rec_col.update(
                            #             {"dpid": loaded_batch['dpid'], "account_no": ac_no, "cycle_ver": cycle_ver},
                            #             {'$set': {'status': 'Syndicated'}}
                            #         )
                            #     except Exception as e:
                            #         mdjlog.error("{} | customer record: {}".format(e, sbjt_d))
                            # else:
                            #     try:
                            #         cust_rec_col.update(
                            #             {"dpid": loaded_batch['dpid'], "cust_id": cust_id, "cycle_ver": cycle_ver},
                            #             {'$set': {'status': 'Syndicated'}}
                            #         )  # , upsert=True
                            #     except Exception as e:
                            #         cust_rec_col.update(
                            #             {"dpid": loaded_batch['dpid'], "cust_id": 'NOMETER', "cycle_ver": cycle_ver},
                            #             {'$set': {'status': 'Syndicated'}}
                            #         )

                            # mdjlog.info(cust_rec)
                            dataCount += 1
                            if not dataCount % 5000:
                                mdjlog.info("Syndicating {} data file {} & counting @#{}".format(dp_name, sb2file,
                                                                                                 dataCount))
                            syndicaxn_complt = True
            except Exception as e:
                mdjlog.error(
                    "{} | customer ID {} with account no: {}".format(e, cust_id, ac_no))

        #
        mdjlog.info('\n' + '\n' + '#' * 128)
        structures = int(dataCount)
        mdjlog.info("\n\n{} {} structures processed from file {} @ {}".format(
            str(int(structures)), datCat.upper(), file_dtls['file_name'], right_now()))
        footer = '|'.join(['TLTL', dpid, submxn_pt, str(int(structures))])
        # sb2file_handler.write(footer)
        syndi_data_list.append(footer)
        sb2file_handler = open(syndi_dir + sb2file, 'w')
        sb2file_handler.write('\n'.join(syndi_data_list))
        sb2file_handler.close()

        mdjlog.info("\n\nSyndicated file: {} written @ {}".format(sb2file, right_now()))
        try:
            sb2fi_d = {'dp_name': meta_data['dp_name'], 'batch': meta_data['batch_no'], 'data_cat': datCat,
                       'cycle_ver': meta_data['cycle_ver'], 'status': 'Syndicated', 'structures': structures,
                       'facilities': crdt_data.shape[0], 'subjects': sbjt_data.shape[0], 'dpid': meta_data['dpid'],
                       'sb2file': sb2file, }
        except:
            sb2fi_d = {'dp_name': meta_data['dp_name'], 'batch': meta_data['batch_no'], 'data_cat': datCat,
                       'cycle_ver': meta_data['cycle_ver'], 'status': 'Syndicated', 'structures': structures,
                       'dpid': meta_data['dpid'], 'sb2file': sb2file, }

        sb2fi = SB2FileInfo(**sb2fi_d)
        sb2fi.save()
        if syndicaxn_complt:
            mdjlog.info("Syndication Completed Successfully idx: {} and crdt data: {}".format(idx, crdt_data.shape))
    except Exception as e:
        mdjlog.error("{}".format(e))


@app.task(name='upd8sbdt_recs')
def upd8sjdt_recs(loaded_batch, sbdt_data, cust_rec_col):
    cycle_ver, mdjlog = loaded_batch['cycle_ver'], get_logger(loaded_batch['dp_name'])
    for idx, sbjt_d in sbdt_data.interrows():
        if loaded_batch['in_mod'] in ('cmb', 'fandl', 'iff', 'mfi', 'pmi',):  # , upsert=True
            try:
                ac_no = sbjt_d.account_no
                cust_rec_col.update(
                    {"dpid": loaded_batch['dpid'], "account_no": ac_no, "cycle_ver": cycle_ver},
                    {'$set': {'status': 'Syndicated'}}
                )
            except Exception as e:
                mdjlog.error("{} | customer record: {}".format(e, sbjt_d))
        else:
            cust_id = sbjt_d.cust_id
            try:
                cust_rec_col.update(
                    {"dpid": loaded_batch['dpid'], "cust_id": cust_id, "cycle_ver": cycle_ver},
                    {'$set': {'status': 'Syndicated'}}
                )  # , upsert=True
            except Exception as e:
                cust_rec_col.update(
                    {"dpid": loaded_batch['dpid'], "cust_id": 'NOMETER', "cycle_ver": cycle_ver},
                    {'$set': {'status': 'Syndicated'}}
                )


@app.task(name='upd8crdt_recs')
def upd8crdt_recs(loaded_batch, crdt_data, faci_rec_col):
    cycle_ver, mdjlog = loaded_batch['cycle_ver'], get_logger(loaded_batch['dp_name'])
    for idx, crdt in crdt_data.interrows():
        try:
            ac_no = crdt.account_no
            faci_rec_col.update(
                {"dpid": loaded_batch['dpid'], "account_no": ac_no, "cycle_ver": cycle_ver},
                {'$set': {'status': 'Syndicated'}}
            )
        except Exception as e:
            mdjlog.error("{} | facility record: {}".format(e, crdt))


def syndic8data(crdt_data, sbjt_data, meta_data, datCat):
    mdjlog, sb2files, tasks = get_logger(meta_data['dp_name']), [], []
    try:
        mdjlog.info("syndicating. .. {} credits with {} subjects".format(crdt_data.shape, sbjt_data.shape))
    except:
        mdjlog.info("syndicating. .. {} combined data".format(crdt_data.shape))
    file_dtls = DataFiles.objects(dpid=meta_data['dpid'], status='Loaded').first()  # batch_no=meta_data['batch_no'],
    try:
        dp_name = meta_data['dp_name'].split('_')[0].lower()
        dp_meta = dp_meta_data(dp_name)
        instCat = dp_meta[dp_name][2]
        institution_cat, submxn_pt = dp_meta[dp_name][2], dp_meta[dp_name][1]
        sgmnt = instCat + datCat if instCat != 'cb' else datCat  # meta_data['sgmnt']
        d8reported = file_dtls['date_reported']
        dpid = meta_data['dpid']
        ctgry_dtls = sb2ctgry_file_type_codes(sgmnt)
        # manager = mp.Manager()
        syndi_dir = xtrcxn_area + os.path.sep + meta_data['dp_name'].split('_')[0].upper() + os.path.sep
        mk_dir(syndi_dir)
        # rv = manager.list()
        chunk_size = 45780
        nu_of_chunks = crdt_data.shape[0] // chunk_size + 1
        #
        parts = nu_of_chunks
        # pool = mp.Pool(nu_of_chunks)
        crdt_data_chunks = np.array_split(crdt_data, parts)
        processes = []
        crdt_packs = len(crdt_data_chunks)
        mdjlog.info(
            "should have {} {} from the submission".format(crdt_packs, 'processes' if crdt_packs > 1 else 'process'))
        for e, crdt_data_chunk in enumerate(crdt_data_chunks):
            process_date = datetime.utcnow().strftime('%d-%b-%Y')
            process_time = datetime.utcnow().strftime('%H%M%S')
            data_list_fn = '-'.join([dpid, ctgry_dtls[sgmnt][0].upper(), process_date, process_time]) + '.dlt'
            data_list_hdr = '|'.join(
                ['HDHD', dpid, submxn_pt, d8reported, process_time, process_date, ctgry_dtls[sgmnt][1]])

            data_list_fn = data_list_fn.upper()
            mdjlog.info("{}".format(data_list_fn))
            if meta_data['in_mod'] == 'cdt':
                sbjt_data_chunk = sbjt_data[sbjt_data.cust_id.isin(crdt_data_chunk.cust_id)]
            elif meta_data['in_mod'] in ('cmb', 'fandl', 'iff', 'mfi', 'phed', 'pmi',):
                sbjt_data_chunk = sbjt_data[sbjt_data.account_no.isin(crdt_data_chunk.account_no)]
            sb2files.append(data_list_fn)

            if meta_data['data_type'] == 'combo':
                mdjlog.info("combo data chunk @#{} : {}".format(e, crdt_data_chunk.shape))
                p = mp.Process(target=syndidata,
                               args=[crdt_data_chunk, None, meta_data, dp_meta, datCat, data_list_hdr, data_list_fn], )
                p.start()
                mdjlog.info("Starting a process. ..")
                processes.append(p)
                time.sleep(1)
            else:
                mdjlog.info(" credit data chunk @#{} : {}".format(e, crdt_data_chunk.shape))
                mdjlog.info("subject data chunk @#{} : {}".format(e, sbjt_data_chunk.shape))
                if not sbjt_data_chunk.empty:
                    p = mp.Process(target=syndidata,
                                   args=[crdt_data_chunk, sbjt_data_chunk, meta_data, dp_meta, datCat, data_list_hdr,
                                         data_list_fn], )
                    p.start()
                    mdjlog.info("Starting a process. ..")
                    processes.append(p)

                    time.sleep(1)
                else:
                    mdjlog.info("subject data chunk @#{} : {} is empty".format(e, sbjt_data_chunk.shape))

        for p, rp in enumerate(processes):
            mdjlog.info("Process @# {}".format(p))
            rp.join()
        print('#Kingdom ThinGz')
        return

    except Exception as e:
        mdjlog.error("{}".format(e))
