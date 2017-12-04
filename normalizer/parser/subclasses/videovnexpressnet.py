#!/usr/bin/python
# -*- coding: utf8 -*-

# Done
from normalizer.parser import *


class VideoVnexpressNetParser(SubBaseParser):
    def __init__(self):
        # Bắt buộc phải gọi đầu tiên
        super().__init__()

        # Tên trang web sử dụng kiểu Title Case
        self._source_page = 'VNExpress'

        # Chứa tên miền không có http://www dùng cho parser tự động nhận dạng
        self._domain = 'video.vnexpress.net'

        # Chứa tên miền đầy đủ và không có / cuối cùng dùng để tìm url tuyệt đối
        self._full_domain = 'https://video.vnexpress.net'

        # Custom các regex dùng để parse một số trang dùng subdomain (ví dụ: *.vnexpress.net)
        # self._domain_regex =

        # THAY ĐỔI CÁC HÀM TRONG VARS ĐỂ THAY ĐỔI CÁC THAM SỐ CỦA HÀM CHA

        # Tìm thẻ chứa tiêu đề
        # Gán bằng con trỏ hàm hoặc biểu thức lambda
        self._vars['get_title_tag_func'] = lambda x: x.find('h1', class_='title_detail_video')

        # Tìm thẻ chứa nội dung tóm tắt
        # Gán bằng con trỏ hàm hoặc biểu thức lambda
        # self._vars['get_summary_tag_func'] =

        # Tìm thẻ chứa danh sách các thẻ a chứa keyword bên trong
        # Gán bằng con trỏ hàm hoặc biểu thức lambda
        # self._vars['get_tags_tag_func'] =

        # Tìm thẻ chứa chuỗi thời gian đăng bài
        # Gán bằng con trỏ hàm hoặc biểu thức lambda
        def get_time_tag_func(html):
            div_tag = html.find('div', class_='block_timer')
            a_tag = div_tag and div_tag.a
            if a_tag is not None:
                a_tag.decompose()

            meta_tag = html.find('meta', attrs={'name': 'twitter:image', 'content': True})
            if meta_tag is not None:
                matcher = regex.search(r'\.net\/(\d{4}\/\d{2}\/\d{2})\/',
                                       meta_tag.get('content'), regex.IGNORECASE)
                if matcher is not None:
                    div_tag.append(' - ' + matcher.group(1))
            return div_tag

        self._vars['get_time_tag_func'] = get_time_tag_func

        # Định dạng chuỗi thời gian và trả về đối tượng datetime
        # Gán bằng con trỏ hàm hoặc biểu thức lambda
        def get_datetime_func(string):
            parts = regex.split(r'\s+-\s+', string, regex.IGNORECASE)
            return datetime.strptime('%s %s' % (parts[0], parts[2]), '%H:%M %Y/%m/%d')

        self._vars['get_datetime_func'] = get_datetime_func

        # Chỉ định các nhãn có khả năng là caption
        # Gán bằng danh sách ['A', 'B', ..., 'Z']
        # Mặc định: ['desc', 'pic', 'img', 'box', 'cap', 'photo', 'hinh', 'anh']
        # self._vars['caption_classes'] =

        # Chỉ định các nhãn có khả năng là author
        # Gán bằng danh sách ['A', 'B', ..., 'Z']
        # Mặc định: ['author', 'copyright', 'source', 'nguon', 'tac-gia', 'tacgia']
        # self._vars['author_classes'] =

        # Chỉ định thẻ chứa nội dung chính
        # Gán bằng con trỏ hàm hoặc biểu thức lambda
        self._vars['get_main_content_tag_func'] = lambda x: x.find('div', class_='lead_detail_video')

        # Chỉ định thẻ chứa tên tác giả
        # Khi sử dụng thẻ này thì sẽ tự động không sử dụng tính năng tự động nhận dạng tên tác giả
        # Gán bằng con trỏ hàm hoặc biểu thức lambda
        def get_author_tag_func(html):
            tag = html.find('div', class_='author_mail')
            return tag and tag.find('strong')

        self._vars['get_author_tag_func'] = get_author_tag_func

        # Chỉ định các nhãn được phép và không được phép dùng để dự đoán author
        # Các nhãn: author, center, right, bold, italic
        # Phân cách nhau bởi dấu | và những nhãn nào không được phép thì có tiền tố ^ ở đầu
        # Ví dụ: 'right|bold|author|^center|^italic'
        # self._vars['author_classes_pattern'] =

        # Chỉ định tự động xóa tất cả các chuỗi bên dưới tác giả
        # Thích hợp khi bài viết chèn nhiều quảng cảo, links bên dưới mà không có id để xóa
        # Gán bằng True / False
        # self._vars['clear_all_below_author'] = True

        # Trả về url chứa hình ảnh thumbnail được lưu ở thẻ bên ngoài nội dung chính
        # Mặc định sẽ tự động nhận dạng
        # Gán bằng con trỏ hàm hoặc biểu thức lambda
        # self._vars['get_thumbnail_url_func'] =

        # Biến vars có thể được sử dụng cho nhiều mục đích khác
        # self._vars[''] =

    # Hàm xử lí video có trong bài, tùy mỗi player mà có cách xử lí khác nhau
    # Khi xử lí xong cần thay thế thẻ đó thành thẻ video theo format qui định
    # Nếu cần tìm link trực tiếp của video trên youtube thì trong helper có hàm hỗ trợ
    # def _handle_video(self, html, default_thumbnail_url=None, timeout=15):
    #     return super()._handle_video(html, default_thumbnail_url, timeout)

    # Sử dụng khi muốn xóa phần tử nào đó trên trang để việc parse được thuận tiện
    # def _pre_process(self, html):
    #     return super()._pre_process(html)

    # Sử dụng khi muốn xóa phần tử nào đó trên trang để việc parse được thuận tiện
    def _post_process(self, html):
        # Thumbnail
        thumbnail_url = self._get_thumbnail(html)
        if self._is_valid_image_url(url=thumbnail_url):
            video_thumbnail_url = thumbnail_url

        tag = html.find_parent('html')
        tag = tag and tag.find('div', id='content_script')
        tag = tag and tag.script
        if tag is not None:
            script_code = tag.text

            # Video URL
            matcher = regex.findall(r"s\d+:\s*'([^']+)'", script_code, regex.IGNORECASE)
            if len(matcher) > 0:
                video_url = matcher[-1]
                new_video_tag = create_video_tag(src=video_url, thumbnail=video_thumbnail_url,
                                                 mime_type=self._get_mime_type_from_url(url=video_url))
                html.append(new_video_tag)

        return super()._post_process(html)

    def _get_tags(self, html):
        return super()._get_meta_keywords(html)

    def _parse(self, url, html, timeout=15):
        tag = html.find('div', id='content_script')
        tag = tag and tag.script
        if tag is None:
            return None

        script_code = tag.text
        matcher = regex.search(r"VideoVNE.page_url = '([^']+)'", script_code, regex.IGNORECASE)
        if matcher is None:
            return None

        video_page_url = matcher.group(1)
        raw_html = self._get_html(url=video_page_url, timeout=timeout)
        if raw_html is None:
            return None

        return super()._parse(video_page_url, get_soup(raw_html), timeout)