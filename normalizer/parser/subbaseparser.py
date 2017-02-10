#!/usr/bin/python
# -*- coding: utf8 -*-
from abc import abstractmethod

import bleach
from bs4 import NavigableString

from helpers import *
from normalizer.parser import BaseParser


class SubBaseParser(BaseParser):
    def __init__(self):
        super().__init__()

    # Hàm trả về mobile url nếu có
    def _get_mobile_url(self, html, url):
        return url

    # Hàm trả về tiêu đề bài viết
    def _get_post_title(self, html):
        get_title_tag_func = self._vars.get('get_title_tag_func')
        title_tag = html.title if get_title_tag_func is None else get_title_tag_func(html)
        if title_tag is None:
            return None
        return normalize_string(title_tag.text) if is_valid_string(title_tag.text) else None

    # Hàm lấy danh sách các keywords có trong thẻ meta
    def _get_meta_keywords(self, html):
        meta_tag = html.find('meta', attrs={'name': 'keywords', 'content': True})
        if meta_tag is None:
            return None

        keywords = meta_tag.get('content').split(',')
        normalized_keywords = []
        for keyword in keywords:
            if is_valid_string(keyword):
                normalized_keywords.append(normalize_string(keyword))
        return ', '.join(normalized_keywords)

    # Hàm lấy phần mô tả trong thẻ meta
    def _get_meta_description(self, html):
        meta_tag = html.find('meta', attrs={'name': 'description', 'content': True})
        if meta_tag is None:
            return None

        content = meta_tag.get('content')
        return normalize_string(content) if is_valid_string(content) else None

    # Hàm lấy phần mô tả chính
    def _get_summary(self, html):
        get_summary_tag_func = self._vars.get('get_summary_tag_func')
        if get_summary_tag_func is None:
            return None

        summary_tag = get_summary_tag_func(html)
        if summary_tag is None:
            return None

        content = summary_tag.text
        return normalize_string(content) if is_valid_string(content) else None

    # Hàm lấy danh sách keywords
    def _get_tags(self, html):
        get_tags_tag_func = self._vars.get('get_tags_tag_func')
        if get_tags_tag_func is None:
            return None

        tags_tag = get_tags_tag_func(html)
        if tags_tag is None:
            return None

        normalized_keywords = []
        for a_tag in tags_tag.find_all('a'):
            keyword = a_tag.text
            if is_valid_string(keyword):
                normalized_keywords.append(normalize_string(keyword))
        return ', '.join(normalized_keywords)

    # Hàm lấy ngày của bài đăng
    def _get_publish_date(self, html):
        get_time_tag_func = self._vars.get('get_time_tag_func')
        get_datetime_func = self._vars.get('get_datetime_func')
        if get_time_tag_func is None or get_datetime_func is None:
            return None

        time_tag = get_time_tag_func(html)
        if time_tag is None:
            return None

        return get_datetime_func(normalize_string(time_tag.text))

    @abstractmethod
    def _handle_video(self, html, timeout=15):
        pass

    def _handle_image(self, html, title=None):
        img_tags = html.find_all('img')
        for img_tag in img_tags:
            img_tag['src'] = self._get_valid_image_url(img_tag.get('src'))
            next_tag = img_tag.find_next(True)
            if next_tag.name == 'div':
                classes = next_tag.get('class')
                if classes is not None and ('center' in classes or 'image' in classes):
                    caption_tag = create_caption_tag(next_tag.text)
                    next_tag.replace_with(caption_tag)
        return html

    # Mỗi đầu báo có thể kế thừa hàm này để xử lí 1 số trường hợp riêng bị như xóa ads,...
    def _pre_process(self, html):
        return html

    @staticmethod
    def _get_special_tag_classes(tag):
        classes = tag.get('class')
        if classes is None:
            classes = []

        # Kiểm tra trong align
        align = tag.get('align')
        if align is not None:
            align = align.lower()
            if 'center' in align:
                classes.append('center')
            elif 'right' in align:
                classes.append('right')

        # Kiểm tra trong style
        style = tag.get('style')
        if style is not None:
            style = style.lower()
            if 'center' in style:
                classes.append('center')
            elif 'right' in style:
                classes.append('right')

        # Kiểm tra tên thẻ
        if tag.name in ['table', 'td', 'caption', 'figcaption']:
            classes.append('image')
        elif tag.name in ['strong', 'b']:
            classes.append('bold')
        elif tag.name in ['em', 'i']:
            classes.append('italic')
        elif tag.name in ['center']:
            classes.append('center')

        return list(set(classes))

    @staticmethod
    def _combine_span_tags(span_tag, block_classes=None):
        if span_tag is None or isinstance(span_tag, NavigableString) or span_tag.name != 'span':
            return None

        # Wrap lại bằng div để tránh rời rạc
        span_tag.wrap(create_html_tag('div'))

        parent_span_tag = span_tag.parent

        if block_classes is None:
            block_classes = []

        span_classes = span_tag.get('class')
        if span_classes is None:
            span_classes = []

        span_classes.extend(block_classes)

        s = [(span_tag, list(set(span_classes)))]

        while len(s) > 0:
            tag, classes = s.pop()

            current_tag = tag

            # Lặp qua từng node con
            children = list(tag.children)

            if len(children) > 0:
                temp_tag = create_html_tag('span', attrs={'class': classes} if len(classes) > 0 else {})

                for child_tag in children:
                    if isinstance(child_tag, NavigableString):
                        temp_tag.append(child_tag.extract())
                    else:
                        # Bổ sung thẻ span vào cây nếu có dữ liệu, chỉ nhận thẻ span chứa nội dung có ý nghĩa
                        if len(temp_tag.contents) > 0:
                            # Chèn vào sau thẻ cha
                            current_tag.insert_after(temp_tag)
                            if not is_valid_string(temp_tag.text, r'\s+'):
                                temp_tag.unwrap()

                            current_tag = current_tag.next_sibling
                            temp_tag = create_html_tag('span', attrs={'class': classes} if len(classes) > 0 else {})

                        if child_tag.name == 'br':
                            current_tag.insert_after(child_tag.extract())
                            current_tag = current_tag.next_sibling
                        else:
                            # Lấy thẻ span con ra để khi thẻ cha bị xóa thì không bị xóa theo
                            child_span_tag = child_tag.extract()

                            span_classes = child_tag.get('class')
                            if span_classes is None:
                                span_classes = []

                            span_classes.extend(classes)

                            if len(child_span_tag.contents) > 0:
                                current_tag.insert_after(child_span_tag)
                                current_tag = current_tag.next_sibling
                                s.append((child_span_tag, list(set(span_classes))))
                            else:
                                child_span_tag.decompose()

                # Trường hợp không có tag để đóng lại
                if len(temp_tag.contents) > 0:
                    # Chèn vào sau thẻ cha
                    current_tag.insert_after(temp_tag)
                    if not is_valid_string(temp_tag.text, r'\s+'):
                        temp_tag.unwrap()

            # Xóa thẻ cha vì con của nó đã được đem lên cùng cấp nằm ở phía sau
            tag.decompose()

        return parent_span_tag

    @staticmethod
    def _combine_span_sibling_tags(div_tag):
        if div_tag is None or isinstance(div_tag, NavigableString) or div_tag.name != 'div':
            return None

        children = list(div_tag.children)
        children_size = len(children)

        i = 0
        while i < children_size - 1:
            child_tag = children[i]

            if child_tag.name == 'span':

                j = i + 1
                while j < children_size:
                    next_sibling = children[j]

                    if isinstance(next_sibling, NavigableString):
                        if is_valid_string(str(next_sibling), r'\s+'):
                            break
                        else:
                            # Gộp thẻ span và text gồm các khoảng trắng
                            child_tag.append(next_sibling.extract())
                            i = j
                    else:
                        if next_sibling.name == 'span':
                            # Xử lí gộp hai span kề nhau có chung class
                            child_classes = child_tag.get('class')
                            if child_classes is None:
                                child_classes = []

                            next_sibling_classes = next_sibling.get('class')
                            if next_sibling_classes is None:
                                next_sibling_classes = []

                            if set(child_classes) == set(next_sibling_classes):
                                # Gộp 2 thẻ span
                                child_tag.append(next_sibling.extract())
                                next_sibling.unwrap()
                                i = j
                            else:
                                break
                        else:
                            break
                    j += 1

                # Gộp các string liền kề bên trong span
                child_tag.string = child_tag.text

            i += 1

        # Nếu thẻ div chỉ chứa 1 span thì gộp class của span đó với div bao bên ngoài
        child_tags = div_tag.find_all(True)
        if len(child_tags) == 1 and child_tags[0].name == 'span':
            previous_sibling = all(
                isinstance(sibling, NavigableString) and not is_valid_string(sibling, r'\s+') for sibling in
                child_tags[0].previous_siblings)
            next_sibling = all(
                isinstance(sibling, NavigableString) and not is_valid_string(sibling, r'\s+') for sibling in
                child_tags[0].next_siblings)
            if previous_sibling and next_sibling:
                div_classes = div_tag.get('class')
                if div_classes is None:
                    div_classes = []

                child_classes = child_tags[0].get('class')
                if child_classes is None:
                    child_classes = []

                div_classes.extend(child_classes)
                div_tag.attrs = {'class': list(set(div_classes))}
                child_tags[0].unwrap()

    @staticmethod
    def _combine_div_tags(parent_tag):
        if parent_tag is None or isinstance(parent_tag, NavigableString) or parent_tag.name != 'div':
            return None

        # Clone thẻ div để khi unwrap vẫn không bị mất.
        parent_tag.wrap(create_html_tag('div', attrs=parent_tag.attrs))
        bounding_tag = parent_tag.parent

        classes = parent_tag.get('class')
        s = [(parent_tag, [] if classes is None else classes)]

        while len(s) > 0:
            tag, classes = s.pop()

            # Lặp qua từng node con
            children = list(tag.children)
            children_size = len(children)

            if children_size > 0:
                temp_tag = create_html_tag('div', attrs={'class': classes} if len(classes) > 0 else {})

                i = 0
                while i < children_size:
                    child_tag = children[i]

                    if isinstance(child_tag, NavigableString):
                        temp_tag.append(child_tag.extract())
                    elif child_tag.name == 'span':
                        span_tags = SubBaseParser._combine_span_tags(span_tag=child_tag,
                                                                     block_classes=temp_tag.attrs.get('class'))

                        contents = list(span_tags.children)
                        for child in contents:
                            if child.name == 'br':
                                if len(temp_tag.contents) > 0 and is_valid_string(temp_tag.text, r'\s+'):
                                    span_tags.insert_before(temp_tag)

                                    # Gộp các span anh em có chung class
                                    SubBaseParser._combine_span_sibling_tags(div_tag=temp_tag)

                                    temp_tag = create_html_tag('div',
                                                               attrs={'class': classes} if len(classes) > 0 else {})
                            else:
                                temp_tag.append(child.extract())

                        span_tags.decompose()
                    else:
                        # Bổ sung thẻ div vào cây nếu có dữ liệu, chỉ nhận thẻ div chứa nội dung có ý nghĩa
                        if len(temp_tag.contents) > 0 and is_valid_string(temp_tag.text, r'\s+'):
                            child_tag.insert_before(temp_tag)

                            # Gộp các span anh em có chung class
                            SubBaseParser._combine_span_sibling_tags(div_tag=temp_tag)

                            temp_tag = create_html_tag('div', attrs={'class': classes} if len(classes) > 0 else {})

                        if child_tag.name == 'div':
                            # Thêm vào stack nếu là div
                            child_classes = child_tag.get('class')
                            if child_classes is None:
                                child_classes = []
                            child_classes.extend(classes)
                            if len(child_tag.contents) > 0 and (
                                        is_valid_string(child_tag.text, r'\s+') or child_tag.find(
                                        ['video', 'img']) is not None):
                                s.append((child_tag, list(set(child_classes))))
                            else:
                                child_tag.decompose()
                        else:
                            if child_tag.name not in ['video', 'img']:
                                child_tag.decompose()

                    i += 1

                # Trường hợp không có tag để đóng lại, chỉ nhận thẻ div chứa nội dung có ý nghĩa
                if len(temp_tag.contents) > 0 and is_valid_string(temp_tag.text, r'\s+'):
                    # Đã duyệt qua tất cả thẻ con nên chỉ cần append để vào vị trí cuối
                    tag.append(temp_tag)

                    # Gộp các span anh em có chung class
                    SubBaseParser._combine_span_sibling_tags(div_tag=temp_tag)

                # Xóa thẻ div ngoài cùng nhưng vẫn giữ các thẻ con bên trong nó
                tag.unwrap()
            else:
                # Xóa thẻ div nếu nó không có thẻ con
                tag.decompose()

        return bounding_tag

    def _normalize_content(self, html, title=None, timeout=15):
        get_main_content_tag_func = self._vars.get('get_main_content_tag_func')
        if get_main_content_tag_func is None:
            return None

        main_content_tag = get_main_content_tag_func(html)
        if main_content_tag is None:
            return None

        # Xóa rác
        main_content_tag = self._pre_process(html=main_content_tag)

        # Xử lí thẻ video
        main_content_tag = self._handle_video(html=main_content_tag, timeout=timeout)

        # Chuẩn hóa
        main_content_tag.name = 'main'

        # Chuẩn hóa thẻ
        tags = main_content_tag.find_all(
            ['div', 'p', 'table', 'td', 'caption', 'figcaption', 'center', 'strong', 'b', 'em', 'i'])
        for tag in tags:
            classes = self._get_special_tag_classes(tag=tag)
            tag.name = 'div' if tag.name in ['div', 'p', 'table', 'td', 'caption', 'figcaption', 'center'] else 'span'
            tag.attrs = {'class': classes} if len(classes) > 0 else {}

        attrs = {
            'video': ['width', 'height'],
            'source': ['src', 'type'],  # Controls
            'img': ['src', 'alt'],
            'div': ['class'],
            'span': ['class']
        }

        main_content_tag = bleach.clean(main_content_tag, tags=['main', 'div', 'br', 'video', 'source', 'img', 'span'],
                                        attributes=attrs, strip=True, strip_comments=True)

        main_content_tag = get_soup(main_content_tag, clear_special_chars=True).main
        main_content_tag.name = 'div'

        main_content_tag = self._combine_div_tags(parent_tag=main_content_tag)

        # Xử lí thẻ image
        main_content_tag = self._handle_image(html=main_content_tag, title=title)

        main_content_tag.name = 'main'
        main_content_tag.attrs = {}

        return main_content_tag

    def _get_author(self, html):
        authors = []
        div_tags = html.find_all('div', class_='bold')
        div_tags = list(reversed(div_tags))

        size = len(div_tags)
        i = 0

        while i < size:
            div_tag = div_tags[i]

            classes = div_tag.get('class')
            string = div_tag.text
            if not string.endswith('.') and classes is not None and 'bold' in classes:
                if 'right' in classes:
                    authors.insert(0, string)
                    if i == size - 1:
                        break

                    while div_tag.previous_sibling == div_tags[i + 1]:
                        authors.insert(0, div_tags[i + 1].text)
                        i += 1
                    break
            i += 1
        return '\n'.join(authors)

    # Trả về url của ảnh đầu tiên trong content
    def _get_thumbnail(self, html):
        img_tag = html.find('img', attrs={'src': True})
        if img_tag is None:
            return None
        return img_tag.get('src')

    def _get_content(self, html):
        if html is None:
            return None

        # Unwrap thẻ inline
        tags = html.find_all('span')
        for tag in tags:
            tag.unwrap()

        # Đổi thẻ block sang <p></p> và chuẩn hóa nội dung
        tags = html.find_all('div')
        for tag in tags:
            tag.name = 'p'
            tag.attrs = {}
            tag.string = normalize_string(tag.text)

        content = html.decode(formatter=None)
        return regex.sub(r'<main>|<\/main>', '', content)

    # Hàm trả về nội dung đã lọc thẻ html
    def _get_plain(self, html):
        if html is None:
            return None

        lines = []

        tags = html.find_all('p')
        for tag in tags:
            if tag.get('class') is None:
                lines.append(normalize_string(tag.text))

        return ' '.join(lines)

    # Hàm chính để gọi các hàm con và tạo kết quả
    def _parse(self, url, html, timeout=15):
        alias = self._get_alias(url=url)
        mobile_url = self._get_mobile_url(html=html, url=url)
        post_title = self._get_post_title(html=html)
        meta_keywords = self._get_meta_keywords(html=html)
        meta_description = self._get_meta_description(html=html)

        publish_date = self._get_publish_date(html=html)
        tags = self._get_tags(html=html)
        summary = self._get_summary(html=html)

        normalized_content = self._normalize_content(html=html, title=remove_special_chars(post_title), timeout=timeout)
        author = self._get_author(html=normalized_content)
        thumbnail = self._get_thumbnail(html=normalized_content)
        content = self._get_content(html=normalized_content)
        plain = self._get_plain(html=normalized_content)

        return self._build_json(url=url, mobile_url=mobile_url, title=post_title, alias=alias,
                                meta_keywords=meta_keywords, meta_description=meta_description,
                                publish_date=publish_date, author=author, tags=tags, thumbnail=thumbnail,
                                summary=summary, content=content, plain=plain)
