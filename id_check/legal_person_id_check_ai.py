import regex
from datetime import datetime

from core.db.local_file.get_info import cached_file


def id_card_format(papers_type, invalid_date, if_invalid):
    r = {
        '证件类型': papers_type,
        '失效日期': invalid_date,
        '是否失效': if_invalid,
    }
    return r


# 把 20220511 转换为 2022-05-11 或其他需要的格式
def convert_numbers_to_date(num_str):
    if not len(num_str) == 8:
        return num_str
    num_list = list(num_str)
    num_list.insert(4, '-')
    num_list.insert(7, '-')
    the_date = ''.join(num_list)
    return the_date


def id_card_info(id_card_ocr_info):
    first = ['姓名', '性别', '民族', '出生', '住址', '公民身份号码']
    second = ['中华人民共和国', '居民身份证']
    for i, info in enumerate(id_card_ocr_info):
        if not info.get('ID_CARD') == 'ID_CARD':
            card_type = '这不是身份证, 请重新上传'
            info = id_card_format(card_type, '', '')
            return info
        id_name = ''  # 身份证姓名
        card_type = '身份证'
        words = info.get('words')
        if '中华人民共和国' in second and '居民身份证' in second:
            card_type = '身份证（国徽面）'
        elif '姓名' in first and '民族' in first:
            card_type = '身份证（个人信息面）'
        card_type = '身份证'  # 证件类型

        invalid_date = info['info']['words_result']['失效日期']
        inv_date = convert_numbers_to_date(invalid_date)  # 失效日期
        today = datetime.today()
        test_t = today[0:10]
        today_date = today[0:10]
        current_date = today_date.replace('-', '')
        if_invalid = int(current_date) - int(invalid_date)
        is_invalid = False  # 是否失效
        if if_invalid > 0:
            is_invalid = True

        result = id_card_format(card_type, inv_date, is_invalid)
        return result


if __name__ == '__main__':
    t1 = r"https://cpzx-bswjjc.s3.cn-north-1.jdcloud-oss.com/s3/2022/05/10/yn_bsxsd/0b0544ad-c2a1-4579-8d84-24ff478aa45a.pdf?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Date=20220510T094432Z&X-Amz-SignedHeaders=host&X-Amz-Expires=86400&X-Amz-Credential=B79F08C894D9E9407FC071CE40398503%2F20220510%2Fcn-north-1%2Fs3%2Faws4_request&X-Amz-Signature=dafa40072438d442d70e82ac0c5525c93b4a4904a1a33017118f5885f77b4747"
    t2 = r"https://cpzx-bswjjc.s3.cn-north-1.jdcloud-oss.com/s3/2022/05/10/yn_bsxsd/0b0544ad-c2a1-4579-8d84-24ff478aa45a.pdf?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Date=20220510T094432Z&X-Amz-SignedHeaders=host&X-Amz-Expires=86400&X-Amz-Credential=B79F08C894D9E9407FC071CE40398503%2F20220510%2Fcn-north-1%2Fs3%2Faws4_request&X-Amz-Signature=dafa40072438d442d70e82ac0c5525c93b4a4904a1a33017118f5885f77b4747"
    t3 = r"https://cpzx-bswjjc.s3.cn-north-1.jdcloud-oss.com/s3/2022/05/10/yn_bsxsd/394a530b-2ad3-4deb-be92-25de6b2a7f08.pdf?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Date=20220510T100016Z&X-Amz-SignedHeaders=host&X-Amz-Expires=86400&X-Amz-Credential=B79F08C894D9E9407FC071CE40398503%2F20220510%2Fcn-north-1%2Fs3%2Faws4_request&X-Amz-Signature=9c8dc917fb3de75d7ba3e4cec178357cc10be0aca75f3fd59edaf10bef60895c"
    # res = cached_file(t2, l=['fddbrjc'], remark=2)
    # print(res)
    res = convert_numbers_to_date('20220105')
    print(res)