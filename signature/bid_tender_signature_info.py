import os
import time

from core.cust_tasks.signature.bid_signature_info import sort_result as bid_seal
from core.cust_tasks.signature.tender_signature_info import output_contrast_res as tender_seal
from core.cust_tasks.signature.rules import base_tender_sign_words
from core.cust_tasks.tender_func.bidder_name_info import person_summary
from core.db import cached_file

from core.cust_tasks.shared_const import FIT, ERROR, NOT_DETECTED, NON_RECOGNIZE, READ, SKIP, NOT_SURE, NOT_GIVEN


# 去重
def rm_repeat_elements(data):
    data_list = list()
    if isinstance(data, list):
        for i in data:
            if i not in data_list:
                data_list.append(i)
    return data_list


# 获取招标书印章对比结果及其标题
def bid_seal_titles(bid_path):
    bid_seals = bid_seal(bid_path)
    bid_titles = list()
    for bid_title in bid_seals:
        # bid_titles.append(bid_title[1])
        bid_titles.append([bid_title[1], bid_title[2]['index']])

    return rm_repeat_elements(bid_titles)


# 获取投标书印章对比结果及其标题/印章对比结果
def tender_seal_titles(tender_path, person_summary):
    tender_seals = tender_seal(tender_path, person_summary)

    tender_titles = list()
    for tender_title in tender_seals:
        title = tender_title['标题']
        seal_res = tender_title['印章是否符合']
        page_index = tender_title['页码']
        tender_titles.append([title, seal_res, page_index])
        # tender_titles.append({title: seal_res})

    # tender_titles.sort(key=lambda x: tender_titles[2].values())

    return tender_titles


# 给投标页码排序
def sort_tender_pages(tender_path, person_summary):
    tender_titles = tender_seal_titles(tender_path, person_summary)
    for i in range(len(tender_titles)):
        for j in range(i + 1, len(tender_titles)):
            for pi, vi in tender_titles[i][2].items():
                # print(vi)
                for pk, vk in tender_titles[j][2].items():
                    if pi > pk:
                        tender_titles[i], tender_titles[j] = tender_titles[j], tender_titles[i]
    return tender_titles


# 投标文件添加非必要标题, 如果招标文件要求, 投标文件没有, 则招标文件也不需输出
def add_no_nec_titles(bid_path, tender_path, person_summary):
    bid_titles = bid_seal_titles(bid_path)

    temp_bid_title = list()
    for title in bid_titles:
        temp_bid_title.append(title[0])
    tender_titles = tender_seal_titles(tender_path, person_summary)

    base_words = base_tender_sign_words # 获取非必要标题索引

    temp_titles = list()
    for i in tender_titles:
        temp_titles.append(i[0])

    for title in bid_titles:
        if (title[0] in base_words) and (title[0] not in temp_titles):
            bid_titles.remove(title)

    return bid_titles


# 对比招投标文件的标题
def result_style(bid_title, tender_title, status):
    index = list()
    if status == NON_RECOGNIZE:
        index = []
    else:
        index = [x for x in tender_title[2].values()]
    res = {
        'cat': bid_title[0],
        'req': f'《{bid_title[0]}》盖章',
        'real_res': f'《{bid_title[0]}》盖章{status}',
        'status': status,
        'bid_index': bid_title[1],
        'index': index,
        }
    return res


# 对比招投标文件的标题
def title_contrast(bid_path, tender_path, person_summary):
    bid_titles = add_no_nec_titles(bid_path, tender_path, person_summary)
    tender_titles = sort_tender_pages(tender_path, person_summary)

    temp_titles = list()
    for i in tender_titles:
        temp_titles.append(i[0])

    t_titles = rm_repeat_elements(temp_titles)

    contrast_res = list()
    print(tender_titles)
    for i in tender_titles:
        for bid_title in bid_titles:
            if i[0] == bid_title[0]:       # 投标标题响应了招标标题
                if i[1] == '是':
                    res1 = result_style(bid_title, i, FIT)
                    contrast_res.append(res1)
                    break
                elif i[1] == '否':
                    res2 = result_style(bid_title, i, ERROR)
                    contrast_res.append(res2)
                    break
                elif i[1] == '未盖章':
                    res4 = result_style(bid_title, i, NON_RECOGNIZE)
                    contrast_res.append(res4)
                    break
    for i in tender_titles:
        for bid_title in bid_titles:
            if bid_title[0] not in t_titles:       # 标题没有响应, 结果不符合
                res3 = result_style(bid_title, i, NON_RECOGNIZE)
                contrast_res.append(res3)
                bid_titles.remove(bid_title)
                break

    # 去重 & 返回
    a = rm_repeat_elements(contrast_res)
    ret = modify_ret_func(a)
    for singular_type in ret["singular_type"]:
        for singular_detail in singular_type["singular_detail"]:
            singular_type.update(singular_detail)
            singular_group = '投标文件响应招标要求'
            if singular_detail['status'] == NON_RECOGNIZE or singular_detail['status'] == ERROR:
                singular_group = "没有响应招标要求"
            singular_type['singular_group'] = singular_group
            break
    return ret


def modify_ret_func(a):
    ret = {"name": "盖章检查", "req": "招标文件要求投标文件盖章的检查", "key": "gzjc", "isLeaf": True, "singular_type": []}
    cat_list = list(set([name_info["cat"] for name_info in a]))
    for dic in a:
        if not dic.get("index"):
            dic["img_idx"] = []
            dic["t_index"] = []
        if dic["index"] and isinstance(dic["index"][0], str):
            dic["img_idx"] = [int(dic["index"][0])]
            dic["t_index"] = []
        if dic["index"] and isinstance(dic["index"][0], int):
            dic["img_idx"] = []
            dic["t_index"] = [int(dic["index"][0])]
        dic["res"] = dic.pop("real_res")
        if dic["status"] in (NOT_GIVEN):
            dic["option"] = SKIP
        else:
            dic["option"] = READ
    for name_info in cat_list:
        dic = {}
        dic["name"] = name_info
        dic["singular_detail"] = list()
        dic["singular_detail"].extend([i for i in a if i["cat"] == name_info])
        dic["singular_num"] = len([i for i in a if i["status"] in (ERROR, NOT_GIVEN) and i["cat"] == name_info])
        ret["singular_type"].append(dic)
    ret["total"] = len(a)
    ret['correct'] = sum(map(lambda x: x['status'] == FIT, a))
    ret['err_amount'] = sum(map(lambda x: x['status'] in (ERROR, NOT_GIVEN), a))
    ret['not_sure'] = ret["total"] - ret['correct'] - ret['err_amount']

    return ret


if __name__ == '__main__':

    # # 南固碾
    b_new_path = r"C:\Users\59793\Desktop\new_folder\南固碾城中村改造回迁安置用房项目1-招标文件.pdf"
    t1_new_path = r"C:\Users\59793\Desktop\new_folder\投标文件1.pdf"
    # t2_new_path = r"C:\Users\59793\Desktop\new_folder\投标文件2.pdf"
    #
    # # 一汽 奥迪整车
    # b_yiqi_path = r'\\Tlserver\标书文件\work\标书文件\一汽\0a490229-a563-4626-8f4a-f8fed5038ec9\0a490229-a563-4626-8f4a-f8fed5038ec9.pdf'
    # t1_yiqi_path = r'\\Tlserver\标书文件\work\标书文件\一汽\0a490229-a563-4626-8f4a-f8fed5038ec9\91220101732560548K_投标文件正文.pdf'
    # t2_yiqi_path = r'\\Tlserver\标书文件\work\标书文件\一汽\0a490229-a563-4626-8f4a-f8fed5038ec9\91220101776590482P_投标文件正文.pdf'
    #
    # bid_path = r"\\Tlserver\标书文件\work\标书文件\一汽\0a214135-29ff-434e-8034-991eff028328\0a214135-29ff-434e-8034-991eff028328.pdf"
    # tender_path = r"\\Tlserver\标书文件\work\标书文件\一汽\0a214135-29ff-434e-8034-991eff028328\912201011240311675_投标文件格式.pdf"
    # bid_path = r"\\Tlserver\标书文件\work\标书文件\06-山西标书\货物类\1.2021JHJ378 (招标)太原市聋人学校家具竞争性谈判采购\(招标)太原市聋人学校家具竞争性谈判采购 招标文件20210831182427.pdf"
    # tender_path = r"\\Tlserver\标书文件\work\标书文件\06-山西标书\货物类\1.2021JHJ378 (招标)太原市聋人学校家具竞争性谈判采购\1\资格审查部分.pdf"
    # tender_path = r"\\Tlserver\标书文件\work\标书文件\06-山西标书\货物类\1.2021JHJ378 (招标)太原市聋人学校家具竞争性谈判采购\2\资格审查部分.pdf"
    # tender_path = r"\\Tlserver\标书文件\work\标书文件\06-山西标书\货物类\1.2021JHJ378 (招标)太原市聋人学校家具竞争性谈判采购\3\资格审查部分.pdf"


    b_path = r"\\Tlserver\标书文件\work\标书文件\02-昆明标书\06-昆明-市政类标书\20\云南驿迅建筑有限公司_TBZ\ZBWJ.pdf"
    t_path = r"\\Tlserver\标书文件\work\标书文件\02-昆明标书\06-昆明-市政类标书\20\云南驿迅建筑有限公司_TBZ\资格审查文件.pdf"

    b_path = r"\\Tlserver\标书文件\work\标书文件\06-山西标书\03-工程类\南固碾城中村改造回迁安置用房项目1\南固碾城中村改造回迁安置用房项目1-招标文件.pdf"
    t_path = r"\\Tlserver\标书文件\work\标书文件\06-山西标书\03-工程类\南固碾城中村改造回迁安置用房项目1\投标单位1\投标单位1\投标文件.pdf"

    # t_path = r"\\Tlserver\标书文件\work\标书文件\02-昆明标书\05-昆明-设计类标书\7\云南工程勘察设计院有限公司_BTBJ\资格审查文件.pdf"
    # b_path = r"\\Tlserver\标书文件\work\标书文件\02-昆明标书\05-昆明-设计类标书\7\云南工程勘察设计院有限公司_BTBJ\ZBWJ.pdf"
    #
    # b_path = r"C:\Users\59793\Documents\WXWork\1688851091150007\Cache\File\2022-01\招标文件正文-改.pdf"
    # t_path = r"C:\Users\59793\Documents\WXWork\1688851091150007\Cache\File\2022-01\郑州中原铁道工程有限责任公司的投标文件-改错文件.pdf"
    #
    # b_path = r"\\Tlserver\标书文件\work\标书文件\02-昆明标书\06-昆明-市政类标书\28\银鹏科技有限公司_TBJ\ZBWJ.pdf"
    # t_path = r"\\Tlserver\标书文件\work\标书文件\02-昆明标书\06-昆明-市政类标书\28\银鹏科技有限公司_TBJ\项目管理机构评审.pdf"

    t = cached_file(t_path, project=os.path.dirname(t_path))
    b = cached_file(b_path, project=os.path.dirname(b_path))

    person = person_summary(t, {'name': 18})
    # print(person)
    print(tender_seal(t, person))
    print(title_contrast(b, t, person))


