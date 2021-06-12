# import motor
import json
from datetime import datetime
from numbers import Real

import progressbar
from elasticsearch import helpers

from IoCEngine.SHU.amounts import float_numbers
from IoCEngine.SHU.trans4mas import fields2date, normalize_amts
from IoCEngine.celeryio import app
from IoCEngine.commons import (
    cdt_udf_modes, cf, count_down, cs, data_type_dict, fs, getID, ns, submission_type_dict, gs, pos
)
from IoCEngine.config.pilot import es, es_i
from IoCEngine.logger import get_logger
from IoCEngine.utils.data_modes import *
from IoCEngine.utils.file import (pym_db, DataBatchProcess, DataFiles)
from utilities.models import ColumnMapping, InMode, IoCField

# from pymongo import UpdateOne
# from pymongo.errors import BulkWriteError
# from tornado import gen

# dbhs = '172.16.2.23'
dbn = 'IoC'


@app.task(name='route_df')
def route_df(data_tupl):
    # global data_tpl, cols, data_store
    data_batch_no, mdjlogger = None, get_logger(data_tupl[0]['dp_name'])
    data_type, in_mod, out_mod = data_tupl[1], data_tupl[0]['in_mod'], data_tupl[0]['out_mod']
    data_tpl = list(data_tupl)
    df = data_tpl.pop(2)
    df = df[[col for col in df.columns if col is not None]]
    # todo gather_stats(data_tpl)
    try:
        if in_mod in ('cmb', 'iff', 'mfi', 'pmi', 'sb2',):
            if data_type in cs:
                if in_mod == 'cmb':
                    data_tpl, cols, data_store = data_tpl, iff()[in_mod if in_mod != 'iff' else out_mod][
                        data_type], 'corporate_submissions'  # CorporateSubmissions
                    return data2col((data_tpl, cols, data_store, data_type), df)
                    # return ppns(data2col, df, [data_tpl, cols, data_store])
                else:
                    try: ifff = iff()[in_mod if in_mod != 'iff' else out_mod]['comm']
                    except: ifff = iff()[in_mod if in_mod != 'iff' else out_mod][data_type]
                    data_tpl, cols, data_store = data_tpl, ifff, 'corporate_submissions'  # CorporateSubmissions
                    return data2col((data_tpl, cols, data_store, data_type), df)
                    # return ppns(data2col, df, [data_tpl, cols, data_store])
            if data_type in ns:
                if in_mod == 'cmb':
                    data_tpl, cols, data_store = data_tpl, iff()[in_mod if in_mod != 'iff' else out_mod][
                        data_type], 'individual_submissions'  # IndividualSubmissions
                    return data2col((data_tpl, cols, data_store, data_type), df)
                    # return ppns(data2col, df, [data_tpl, cols, data_store])
                else:
                    data_tpl, cols, data_store = data_tpl, iff()[in_mod if in_mod != 'iff' else out_mod][
                        data_type], 'individual_submissions'  # IndividualSubmissions
                    return data2col((data_tpl, cols, data_store, data_type), df)
                    # return ppns(data2col, df, [data_tpl, cols, data_store])
            if data_type in fs:
                if in_mod == 'cmb':
                    data_tpl, cols, data_store = data_tpl, iff()[in_mod if in_mod != 'iff' else out_mod][
                        data_type], 'facility_submissions'  # FacilitySubmissions
                    return data2col((data_tpl, cols, data_store, data_type), df)
                    # return ppns(data2col, df, [data_tpl, cols, data_store])
                else:
                    try: ifff = iff()[in_mod if in_mod != 'iff' else out_mod]['fac']
                    except: ifff = iff()[in_mod if in_mod != 'iff' else out_mod][data_type]
                    data_tpl, cols, data_store = data_tpl, ifff, 'facility_submissions'  # FacilitySubmissions
                    return data2col((data_tpl, cols, data_store, data_type), df)
                    # return ppns(data2col, df, [data_tpl, cols, data_store])
        
        elif in_mod in cdt_udf_modes:
            if data_type in cs:
                data_tpl, cols, data_store = data_tpl, cdt()[data_type], 'corporate_submissions'  # CorporateSubmissions
                return data2col((data_tpl, cols, data_store, data_type), df)
                # return ppns(data2col, df, [data_tpl, cols, data_store])
            if data_type in ns:
                data_tpl, cols, data_store = data_tpl, cdt()[data_type], 'individual_submissions'  # IndividualSubmissions
                return data2col((data_tpl, cols, data_store, data_type), df)
                # return ppns(data2col, df, [data_tpl, cols, data_store])
            if data_type in fs:
                data_tpl, cols, data_store = data_tpl, cdt()[data_type], 'facility_submissions'  # FacilitySubmissions
                return data2col((data_tpl, cols, data_store, data_type), df)
                # return ppns(data2col, df, [data_tpl, cols, data_store])
            if data_type in gs:
                data_tpl, cols, data_store = data_tpl, cdt()[data_type], 'guarantors'  # FacilitySubmissions
                return data2col((data_tpl, cols, data_store, data_type), df)
            if data_type in pos:
                data_tpl, cols, data_store = data_tpl, cdt()[data_type], 'principal_officers'  # FacilitySubmissions
                return data2col((data_tpl, cols, data_store, data_type), df)
        
        elif in_mod in ('fandl',):
            if data_type in cs:
                data_tpl, cols, data_store = data_tpl, fandl()[
                    data_type], 'corporate_submissions'  # CorporateSubmissions
                return data2col((data_tpl, cols, data_store, data_type), df)
                # return ppns(data2col, df, [data_tpl, cols, data_store])
            if data_type in ('cons', 'ndvdl',):
                data_tpl, cols, data_store = data_tpl, fandl()[
                    data_type], 'individual_submissions'  # IndividualSubmissions
                return data2col((data_tpl, cols, data_store, data_type), df)
                # return ppns(data2col, df, [data_tpl, cols, data_store])
            if data_type in fs:
                data_tpl, cols, data_store = data_tpl, fandl()[data_type], 'facility_submissions'  # FacilitySubmissions
                return data2col((data_tpl, cols, data_store, data_type), df)
                # return ppns(data2col, df, [data_tpl, cols, data_store])
        
        elif in_mod in ('c0mf', 'visa',):
            if data_type in ('combo',):
                data_tpl, cols, data_store = data_tpl, c0mf(), 'combined_submissions'  # CombinedSubmissions
                return data2col((data_tpl, cols, data_store, data_type), df)
                # return ppns(data2col, df, [data_tpl, cols, data_store])
            else:
                mdjlogger.error("Specified route for data does not exist!")
        
        elif in_mod in ('phed',):
            if data_type in cs:
                data_tpl, cols, data_store = data_tpl, phed()[
                    data_type], 'corporate_submissions'  # CorporateSubmissions
                return data2col((data_tpl, cols, data_store, data_type), df)
                # return ppns(data2col, df, [data_tpl, cols, data_store])
            if data_type in cf:
                data_tpl, cols, data_store = data_tpl, phed()[data_type], 'facility_submissions'  # FacilitySubmissions
                return data2col((data_tpl, cols, data_store, data_type), df)
                # return ppns(data2col, df, [data_tpl, cols, data_store])
        
        else:
            mdjlogger.info('Sorry dear, route has not been configured for {} input mode'.format(in_mod.upper()))
    
    except Exception as e:
        mdjlogger.error(e)
        return False


def upd8col_mappings(mdjlogger, incols, ioc_cols, in_mod):
    if ioc_cols:
        for incol, ioc_col in ((in_col.upper(), col) for in_col, col in zip(incols, ioc_cols)):
            # mdjlogger.info('{} | {} | {}'.format(incol, ioc_col, in_mod))
            try:
                ioc_field = IoCField.objects(name=ioc_col).first()
                inmode = InMode(in_mod)
                if not ioc_field:
                    ioc_field = IoCField(name=ioc_col)
                    ioc_field.in_mode.append(inmode)
                else:
                    if not inmode in ioc_field.in_mode:
                        # ioc_field.update(in_mode=list(set(ioc_field.in_mode + [in_mod])))
                        ioc_field.in_mode.append(inmode)
                ioc_field.save()
            except Exception as e:
                mdjlogger.warning(e)
            try:
                colmap = ColumnMapping(*(incol, ioc_field))
                colmap.save()
            except Exception as e:
                # mdjlogger.warning(e)
                pass
    else:
        for incol in incols:
            try:
                colmap = ColumnMapping(*(incol.upper()))
                colmap.save()
            except Exception as e:
                mdjlogger.warning(e)


def stream_df(_type, index_col, df):
    i = 0
    for ii in df.itertuples():
        d, i = ii._asdict(), i + 1
        if not i % 35710: count_down(None, 5)
        if not str(d[
                       index_col
                   ]).replace('\\', '').replace('\n', '').replace(' ', '').replace('-', '').replace('_', '').isalpha():
            del d['Index']
            
            if d[index_col]:
                d = {i: d[i] for i in d if d[i] not in ('', None)}
                # d['submission'] = _type.split('_')[0]
                if 'account_no' in df and 'cust_id' in df:
                    d["_id"] = "-".join(
                        (d['dpid'], str(d['cust_id']).strip(), str(d['account_no']).strip(), str(d['cycle_ver'])))
                elif d['submission'] == 'corporate' and d['type'] == 'officer':
                    d["_id"] = "-".join((d['dpid'], str(d['cust_id']).strip(), str(d['last_name']).strip(),
                         str(d['first_name']).strip(), str(d['cycle_ver'])))
                elif d['type'] == 'guarantor':
                    d['_id'] = '-'.join((
                        str(d['dpid']).strip(), str(d['account_no']).strip(), str(d['biz_name']).strip(),
                                         )) if str(d['grntr_type']).strip() == 'corporate' else '-'.join((
                        str(d['dpid']).strip(), str(d['account_no']).strip(), ' '.join((
                            str(d['last_name']).strip(), str(d['first_name']).strip(), ))
                    ))
                else:
                    d["_id"] = "-".join((d['dpid'], str(d[index_col]).strip(), str(d['cycle_ver'])))
                #
                d["_index"], d["_type"] = es_i, 'submissions'  # _type
                del d['ndx']
                yield d


def data2col(args, df):
    data_tpl, cols, data_store, datatype = args[0], args[1], args[2], args[3]
    file_name, mdjlogger = data_tpl[0]['file_name'], get_logger(data_tpl[0]['dp_name'])
    data_batch_info, df_dtls = {}, DataFiles.objects(file_name=data_tpl[0]['file_name']).first()
    df_dtls[datatype] = df.shape[0]
    df_dtls.save()
    # todo
    # upd8col_mappings(mdjlogger, df.columns, cols, data_tpl[0]['in_mod'])
    try:
        data_batch_data = DataBatchProcess.objects(
            cycle_ver=data_tpl[0]['cycle_ver'], dp_name=data_tpl[0]['dp_name'], data_type=data_tpl[0]['data_type']
        ).first()
        batchID = getID() if not data_tpl[0]['batch_no'] else data_tpl[0]['batch_no']
        
        data_batch_info['batch_no'], dp_name = batchID, data_tpl[0]['dp_name']
        
        df.replace(to_replace='NULL', value='', inplace=True)
        df.replace(to_replace='N/A', value='', inplace=True)
        if None in df.columns:
            df = df[[c for c in df.columns if c != None]]
        df.columns, dpid, cycle_ver = cols, data_tpl[0]['dpid'], data_tpl[0]['cycle_ver']
        data_batch_info['dp_name'], df['batch_no'], df['dpid'], df['cycle_ver'] = dp_name, batchID, dpid, str(cycle_ver)
        data_batch_info['dpid'], data_batch_info['cycle_ver'], data_batch_info['file_name'] = dpid, cycle_ver, file_name
        data_batch_info['in_mod'], data_batch_info['out_mod'] = data_tpl[0]['in_mod'], data_tpl[0]['out_mod']
        df['submission'], df['type'] = submission_type_dict[datatype], data_type_dict[datatype]
        
        # mdjlogger.info(data_tpl[0]['in_mod'], data_tpl[0]['data_type'], cs, ns)
        
        if data_tpl[0]['in_mod'] in ('cdt',):
            sf = cs + ns + pos
            ndx = 'cust_id' if datatype in sf else 'account_no'
            ndx = ['cust_id', 'last_name', 'first_name'] if datatype in pos else ndx
            dups_df = df[df.duplicated(subset=ndx, keep='first')]
            mdjlogger.info("{} {}".format(datatype, ndx))
            ndx_nunique = df[ndx].nunique()
            dups = dups_df.shape[0]
            if dups > 0:
                mdjlogger.warn(f'dropping {dups} duplicates from {df.shape[0]} to have {ndx_nunique} unique records')
                #todo log duplicates before dropping 'em. ..
                if datatype not in gs:
                    df.drop_duplicates(subset=ndx if isinstance(ndx, list) else [ndx], keep='last', inplace=True)
            else:
                mdjlogger.info("no duplicates")
        mdjlogger.info("checking counts in d2c {} | data type is {}".format(df.shape[0], data_tpl[1]))
        
        df.fillna('', inplace=True)
        # todo chunks = np.array_split(df, parts)
        # try:
        #     chunks = np.array_split(df, 2)
        # except Exception as e:
        #     mdjlogger.error(e)
        # iii = 0
        # for i in df.index:
        #     print(type(df.ix[i]))
        #     while iii <= 5:
        #         print (df.ix[i])
        #         iii += 1
        #     break
        
        # data_type, df = \
        # for df in chunks:
        #     count_down(None, 5)
        data_type = indexDF(data_store, data_tpl, df, dp_name, mdjlogger)
        
        # todo end chunks = np.array_split(df, parts)
        
        # res = bulkI(INDEX_NAME, bulk_data)
        # ij += 1
        # mdjlogger.info("@{}: errors: {}, duration: {}, count: {}".format(ij, res['errors'], res['took'],
        #                                                                  len(res['items'])))
        # if res['errors']:
        #     mdjlogger.critical("Error indexing data:\n{}".format(json.dumps(res, indent=4)))
        #     rezNDXerrors(INDEX_NAME, data_d, data_store, data_tpl, ndx_d, rec_d, res)
        
        pro_stat = 'Loaded'
        data_batch_info['status'], data_batch_info['data_type'] = pro_stat, data_tpl[0]['data_type']
        try:
            data_batch_info[data_store.split('_')[0]] = df.shape[0]
            if 'facility' in data_batch_data and '_all_' in file_name:
                data_batch_info[data_type] = df.shape[0]
                data_batch_info['facility'] = sum(
                    [data_batch_data[k] for k in data_batch_data._data.keys() if k.endswith('fac')] + [
                        data_batch_info[k] for k in data_batch_info.keys() if k.endswith('fac')])
            else:
                pass
        except Exception as e:
            data_batch_info[data_store.split('_')[0]] = df.shape[0]
        df_dtls.update(status=pro_stat)  # batch_no=batchID,
        
        # try:
        if not data_batch_data:
            data_batch_data = DataBatchProcess(**data_batch_info)
            data_batch_data.save()
        else:
            data_batch_data.update(**data_batch_info)
        # except Exception as e:
        #     data_batch_data.update(**data_batch_info)
        
        data_batch_data.reload()
        data_batch_data.update(segments=list(set(data_batch_data['segments'] + [data_tpl[1]])))
        
        return batchID
    except Exception as e:
        mdjlogger.error(e)


def indexDF(data_store, data_tpl, df, dp_name, mdjlogger):
    if 'int_rate' in df.columns:
        df['int_rate'] = df.int_rate.apply(float_numbers)

    for col in df.columns:
        if col in dates_and_number_fields():
            pass
        else:
            try:
                df[col] = df[col].apply(lambda x: str(x) if x else '')
            except Exception as e:
                mdjlogger.error(f"Field Error: {e} in {col} field")
    if data_store.split('_')[0] in ('facility'):
        # df = trnsfm_amts(data_tpl[0], df)
        df = normalize_amts(data_tpl[0], df)
    df = fields2date(data_tpl[0], df)
    # df.fillna('', inplace=True)
    # df = ppns(trnsfm_amts, df, data_tpl[0], True)
    # df = fields2date(data_tpl[0], df)
    df['status'], df['dp_name'], df['data_file'], data_type = 'Loaded', dp_name, data_tpl[0]['file_name'], data_tpl[1]
    bulk_data, i, _type = [], 0, data_store
    # index_col = 'account_no' if data_tpl[1] in fs+gs else 'cust_id'

    sf = cs + ns + pos
    ndx = 'cust_id' if data_tpl[1] in sf else 'account_no'
    ndx = ['cust_id', 'last_name', 'first_name'] if data_tpl[1] in pos else ndx

    # done in SB2, think it's not needed in IoC
    # if data_tpl[0]['in_mod'] in iff_sb2_modes:
    #     index_col = 'account_no'
    if 'bvn' in df.columns:
        df['bvn'] = df.bvn.apply(lambda x: str(x).replace('.0', '') if str(x).endswith('.0') else str(x))
    if 'cust_id' in df.columns:
        df['cust_id'] = df.cust_id.apply(lambda x: str(x).replace('.0', '') if str(x).endswith('.0') else str(x))
        df['cust_id'] = df.cust_id.apply(lambda x: str(x).replace("'", '').strip())
    if 'account_no' in df.columns:
        df['account_no'] = df.account_no.apply(lambda x: str(x).replace("'", '').strip())
    df.fillna('', inplace=True)
    if isinstance(ndx, list):
        df['ndx'] = df[ndx].apply(lambda x: '|'.join(x), axis=1)
        df.set_index('ndx', inplace=True)
    elif data_type in gs:
        df['ndx'] = df[[
            'account_no', 'grntr_type', 'biz_name', 'last_name', 'first_name'
        ]].apply(lambda x: '|'.join((x[0], x[2])) if (
                x[1].lower() == 'corporate') else '|'.join((x[0], x[3], x[4])), axis=1)
        df.set_index('ndx', inplace=True)
    else:
        df.set_index(ndx, inplace=True)
    df['ndx'] = df.index
    if not isinstance(ndx, list):
        df[ndx] = df.index
    # df['sub_cy'] = datetime.strptime(data_tpl[0].date_reported, "%d-%b-%Y").date()
    df['sub_cy'] = datetime.now()
    df.to_excel(f"{dp_name} {data_type}'s segment for {data_tpl[0]['cycle_ver']} data cycle.xlsx")  # todo remove later
    df_stream = stream_df(_type, 'ndx', df)
    # with progressbar.ProgressBar(max_value=pbmv) as progrbar:
    #     for ii in df.itertuples():
    #         i += 1
    #         d = ii._asdict()
    #         if not str(d[index_col]
    #                    ).replace('\\', ''
    #                              ).replace('\n', '').replace(' ', '').replace('-', '').replace('_', '').isalpha():
    #             del d['Index']
    #             ndx_line = {"index": {"_index": INDEX_NAME, "_type": _type,
    #                                   "_id": "-".join((d['dpid'], str(d[index_col]).strip(), str(d['cycle_ver'])))}}
    #             bulk_data.append(ndx_line)
    #             # od2d4i = {k: v for k, v in d.items() if not str(v).strip() == ''}
    #             od2d4i = {i: d[i] for i in d if d[i] not in ('', None)}
    #             bulk_data.append(od2d4i)
    #             iiid = ndx_line['index']['_id']
    #             ndx_d[iiid], data_d[iiid], rec_d[iiid] = ndx_line, od2d4i, ii
    #             r = i % 57911
    #             if not r:
    #                 ij += 1
    #                 res = bulkI(INDEX_NAME, bulk_data)
    #                 bulk_data = []
    #                 mdjlogger.info("@{}: errors: {}, duration: {}, count: {}".format(ij, res['errors'], res['took'],
    #                                                                                  len(res['items'])))
    #                 if res['errors']:
    #                     mdjlogger.critical("Error indexing data:\n{}".format(json.dumps(res, indent=4)))
    #                     rezNDXerrors(INDEX_NAME, data_d, data_store, data_tpl, ndx_d, rec_d, res)
    #         progrbar.update(i)
    try:
        mdjlogger.info("#IndexinG!")
        bulk_resp = helpers.bulk(es, df_stream, refresh=True)
        mdjlogger.info(f"{bulk_resp=}")
        # es.indices.refresh()
    except Exception as e:
        mdjlogger.error(e)
    mdjlogger.info(". .. about {} {} data indexed".format(df.shape[0], data_type))
    return data_type  # , df


def bulkI(INDEX_NAME, bulk_data):
    count_down(None, 5)
    res = es.bulk(index=INDEX_NAME, body=bulk_data, refresh=True)
    return res


def rezNDXerrors(data_d, data_store, data_tpl, ndx_d, res):
    bulk_data, mdjlogger = [], get_logger(data_tpl[0]['dp_name'])
    i, pbmv = 0, len(res['items'])
    with progressbar.ProgressBar(max_value=pbmv) as progrbar:
        for i_res in res['items']:
            i += 1
            if 'error' in i_res['index']:
                error = i_res['index']['error']
                field, xcpxn_cat, xcpxn_desc = error['reason'], 'Field Value Error', error['caused_by']['reason']
                field = field[field.find('[') + 1:field.find(']')]
                iid, sbjt = i_res['index']['_id'], False if data_store.split('_')[0] in ('facility',) else True
                # todo R3Visit
                # todo db_log_xcpxns(data_tpl[0], data_d[iid], rec_d[iid], (xcpxn_cat, xcpxn_desc,), sbjt, (field,))
                del data_d[iid][field]
                bulk_data.append(ndx_d[iid])
                bulk_data.append(data_d[iid])
                progrbar.update(i)
    
    res = es.bulk(index=es_i, body=bulk_data, refresh=True)
    if res['errors']:
        mdjlogger.critical("Indexing Results:\n{}".format(json.dumps(res, indent=4)))
    mdjlogger.info("Indexing Results:\n{}".format(json.dumps(res, indent=4)))


@app.task(name='collect_dict')
def collect_dict(dp_name, data_type, in_mod, data_store, row_dict):
    mdjlogger = get_logger(dp_name)
    try:
        rec_col = pym_db[data_store]
        if in_mod in ('c0mf', 'cmb', 'fandl', 'iff', 'mfi', 'phed', 'pmi'):
            rec_col.update(
                {"dpid": row_dict['dpid'], "account_no": row_dict['account_no'], "cycle_ver": row_dict['cycle_ver']},
                {'$set': row_dict}, upsert=True
            )
        else:
            if data_type in ('corp', 'ndvdl',):
                rec_col.update(
                    {"dpid": row_dict['dpid'], "cust_id": row_dict['cust_id'], "cycle_ver": row_dict['cycle_ver']},
                    {'$set': row_dict}, upsert=True
                )
            elif data_type in ('corpfac', 'ndvdlfac', 'fac',):
                rec_col.update(
                    {"dpid": row_dict['dpid'], "account_no": row_dict['account_no'],
                     "cycle_ver": row_dict['cycle_ver']},
                    {'$set': row_dict}, upsert=True
                )
    except Exception as e:
        mdjlogger.info(e)


def gather_stats(data_tpl):
    df, file_report_stats = data_tpl[2], {}
    if df.shape[0] > 1:
        # file name
        # total
        if data_tpl[1] in ('commfac', 'consfac', 'fac',):
            # account no
            acno_stats = df.account_no.describe()
            file_report_stats['t_ac_nos'], file_report_stats['u_ac_nos'] = acno_stats['count'], acno_stats['unique']
            # account with no customer
            # balance
            df.outstanding_bal = df.outstanding_bal.apply(lambda x: x if isinstance(x, Real) else 0)
            # currency
        if data_tpl[1] in ('comm', 'commsub',):
            # customer id
            cust_id_stats = df.cust_id.describe()
            file_report_stats['t_corp_custs'], file_report_stats['u_corp_custs'] = cust_id_stats['count'], \
                                                                                   cust_id_stats['unique']
            # customer with no account
            # this will be done during syndication
            # rc number
            df.columns.values[5] = 'biz_reg_no'
            rcno_stats = df.biz_reg_no.describe()
            file_report_stats['t_rc_nos'], file_report_stats['u_rc_nos'] = rcno_stats['count'], rcno_stats['unique']
        if data_tpl[1] in ('cons', 'conssub',):
            # bvn
            bvn_stats = df.bvn.describe()
            file_report_stats['t_bvns'], file_report_stats['u_bvns'] = bvn_stats['count'], bvn_stats['unique']
            # need to do valid bvn
            # customer id
            cust_id_stats = df.cust_id.describe()
            file_report_stats['t_indvdl_custs'], file_report_stats['u_indvdl_custs'] = cust_id_stats['count'], \
                                                                                       cust_id_stats['unique']
            # customer with no account
            # this will be done during syndication
        
        print(file_report_stats)
