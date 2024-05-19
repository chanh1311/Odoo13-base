"""
mkdocs-macros-plugin: https://mkdocs-macros-plugin.readthedocs.io/en/latest
"""


def define_env(env):
    """
    This is the hook for defining variables, macros and filters

    - variables: the dictionary that contains the environment variables
    - macro: a decorator function, to declare a macro.
    - filter: a function with one of more arguments,
        used to perform a transformation
    """

    root_path = '/'
    img_path = '/img'
    website_path = '/website'
    bao_cao = '{}/bao_cao'.format(website_path)
    hang_ngay = '{}/hang_ngay'.format(website_path)
    he_thong = '{}/he_thong'.format(website_path)
    website_general_path = '{}/general_function'.format(website_path)
    quy_trinh = '{}/quy_trinh'.format(website_path)
    hang_nam = '{}/hang_nam'.format(website_path)
    hang_thang = '{}/hang_thang'.format(website_path)


    # for build to display in software like odoo, ckan ~~ with use_directory_urls in conf
    # every software have different directories
    custom_build = 1
    if custom_build:
        new_source_path = '/lk_ngoisao/static/description/site'  # real server path

    site_path = [{'name': '', 'literal_url': 'site_path', 'url': ''},
                 {'name': '', 'literal_url': 'website_login_path', 'url': '{}/login/'.format(website_general_path)},
                 {'name': '', 'literal_url': 'website_user_references_path',
                  'url': '{}/user_references/'.format(website_general_path)},
                 {'name': '', 'literal_url': 'hoc_sinh',
                  'url': '{}/hoc_sinh/'.format(hang_ngay)},
                 {'name': '', 'literal_url': 'gv_nv',
                  'url': '{}/gv_nv/'.format(hang_ngay)},
                 {'name': '', 'literal_url': 'thu_hoc_phi',
                  'url': '{}/thu_hoc_phi/'.format(hang_ngay)},
                 {'name': '', 'literal_url': 'dd_dv_chinh',
                  'url': '{}/dd_dv_chinh/'.format(hang_ngay)},
                 {'name': '', 'literal_url': 'dd_dv_phu',
                  'url': '{}/dd_dv_phu/'.format(hang_ngay)},

                 {'name': '', 'literal_url': 'truong_hoc',
                  'url': '{}/truong_hoc/'.format(hang_nam)},
                 {'name': '', 'literal_url': 'nam_hoc',
                  'url': '{}/nam_hoc/'.format(hang_nam)},
                 {'name': '', 'literal_url': 'khoi_hoc',
                  'url': '{}/khoi_hoc/'.format(hang_nam)},
                 {'name': '', 'literal_url': 'lop_hoc',
                  'url': '{}/lop_hoc/'.format(hang_nam)},
                 {'name': '', 'literal_url': 'dich_vu_chinh',
                  'url': '{}/dich_vu_chinh/'.format(hang_nam)},
                 {'name': '', 'literal_url': 'dich_vu_phu',
                  'url': '{}/dich_vu_phu/'.format(hang_nam)},
                 {'name': '', 'literal_url': 'dich_vu_dua_ruoc',
                  'url': '{}/dich_vu_dua_ruoc/'.format(hang_nam)},
                 {'name': '', 'literal_url': 'dich_vu_do_dung',
                  'url': '{}/dich_vu_do_dung/'.format(hang_nam)},
                 {'name': '', 'literal_url': 'chiet_khau',
                  'url': '{}/chiet_khau/'.format(hang_nam)},
                 

                 {'name': '', 'literal_url': 'nguoi_dung',
                  'url': '{}/nguoi_dung/'.format(he_thong)},
                 {'name': '', 'literal_url': 'nhom',
                  'url': '{}/nhom/'.format(he_thong)},
                 {'name': '', 'literal_url': 'nhat_ky_ht',
                  'url': '{}/nhat_ky_ht/'.format(he_thong)},
                 {'name': '', 'literal_url': 'sao_luu',
                  'url': '{}/sao_luu/'.format(he_thong)},
                 {'name': '', 'literal_url': 'tinh',
                  'url': '{}/tinh/'.format(he_thong)},
                 {'name': '', 'literal_url': 'huyen',
                  'url': '{}/huyen/'.format(he_thong)},
                 {'name': '', 'literal_url': 'xa',
                  'url': '{}/xa/'.format(he_thong)},
                 

                 {'name': '', 'literal_url': 'no',
                  'url': '{}/no/'.format(bao_cao)},
                 {'name': '', 'literal_url': 'no_kho_doi',
                  'url': '{}/no_kho_doi/'.format(bao_cao)},
                 {'name': '', 'literal_url': 'doanh_thu_truong',
                  'url': '{}/doanh_thu_truong/'.format(bao_cao)},
                 {'name': '', 'literal_url': 'doanh_thu_dich_vu',
                  'url': '{}/doanh_thu_dich_vu/'.format(bao_cao)},



                 {'name': '', 'literal_url': 'bieu_hoc_phi',
                  'url': '{}/bieu_hoc_phi/'.format(hang_thang)},
                 {'name': '', 'literal_url': 'dk_dich_vu',
                  'url': '{}/dk_dich_vu/'.format(hang_thang)},
                 {'name': '', 'literal_url': 'so_hoc_phi',
                  'url': '{}/so_hoc_phi/'.format(hang_thang)},
                 {'name': '', 'literal_url': 'kh_tiem_nang',
                  'url': '{}/kh_tiem_nang/'.format(hang_thang)},
                 {'name': '', 'literal_url': 'dv_tiem_nang',
                              'url': '{}/dv_tiem_nang/'.format(hang_thang)},
                 {'name': '', 'literal_url': 'ngay_nghi',
                              'url': '{}/ngay_nghi/'.format(hang_thang)},




                 {'name': '', 'literal_url': 'them_hoc_sinh',
                  'url': '{}/them_hoc_sinh/'.format(quy_trinh)},
                 {'name': '', 'literal_url': 'thu_hp',
                  'url': '{}/thu_hp/'.format(quy_trinh)},
                 {'name': '', 'literal_url': 'tao_so_hp',
                  'url': '{}/tao_so_hp/'.format(quy_trinh)},
                 {'name': '', 'literal_url': 'quy_trinh_kh_tiem_nang',
                  'url': '{}/kh_tiem_nang/'.format(quy_trinh)},
                 {'name': '', 'literal_url': 'quy_trinh_dv_tiem_nang',
                  'url': '{}/dv_tiem_nang/'.format(quy_trinh)},
                 {'name': '', 'literal_url': 'bao_cao_no',
                  'url': '{}/bao_cao_no/'.format(quy_trinh)},


                 ]

    def get_site_name(site_lst, nav_url):
        """ Add site name to site_path based on macros plugin """

        def loop_site(site_dct, site_url):
            for k, v in site_dct.items():
                if isinstance(v, list):
                    for site_child in v:
                        res1 = loop_site(site_child, site_url)
                        if res1:
                            return res1
                # [{'Chức năng chung': [{'Đăng nhập': 'website/general_function/login/index.md'}]
                elif '{}{}'.format(root_path, v) == '{}index.md'.format(site_url):
                    return k

        for site in site_lst:
            res = loop_site(site, nav_url)
            if res:
                return res

    for path in site_path:
        path['name'] = get_site_name(env.conf.nav, path['url'])

    @env.macro
    def get_site_url(literal_nav):
        """ Function to get specific site in site_path based on defined URL """
        current_nav = list(filter(lambda x: x['literal_url'] == literal_nav, site_path))
        if current_nav:
            return current_nav[0]
        return ""

    @env.macro
    def get_nav_url(literal_nav):
        """ Function to get specific site url in site_path based on defined URL. Using to link to other site in UI """
        current_nav = get_site_url(literal_nav)
        if current_nav:
            if custom_build:
                return '{}{}index.html'.format(new_source_path, current_nav['url'])
            return current_nav['url']
        return ""

    @env.macro
    def get_nav_desc(literal_nav):
        """ Function to get specific site name in site_path based on defined URL """
        current_nav = get_site_url(literal_nav)
        if current_nav:
            return current_nav['name']
        return ""

    @env.macro
    def get_site_image(literal_nav, image_name, language=False):
        """ Function to get specific image in site_path based on defined URL and image name """
        cur_lang = '/{}'.format(language) if language else ""
        current_nav = get_site_url(literal_nav)
        if current_nav:
            return '{}{}{}{}{}'.format(new_source_path, cur_lang, img_path, current_nav['url'], image_name)
        return ""

    @env.macro
    def get_site_image_vi(literal_nav, image_name):
        return get_site_image(literal_nav, image_name)

    @env.macro
    def get_site_video(literal_nav, video_name):
        """ Function to get specific video in site_path based on defined URL and video name """
        current_nav = get_site_url(literal_nav)
        if current_nav:
            return '{}{}{}'.format(new_source_path, current_nav['url'].replace('videos', 'video'), video_name)
        return ""
