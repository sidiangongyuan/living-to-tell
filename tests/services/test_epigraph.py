from __future__ import annotations

from writer.services.epigraph import detect_epigraph, strip_epigraph


def _assert_strip_semantics(text: str) -> None:
    epigraph = detect_epigraph(text)
    assert epigraph is not None
    assert strip_epigraph(text) == text[epigraph.end_offset :].lstrip()


def test_detect_epigraph_same_line_attribution():
    text = "你必须先相信某种回声。——《夜航西飞》 柏瑞尔·马卡姆\n\n正文开始。"

    epigraph = detect_epigraph(text)

    assert epigraph is not None
    assert epigraph.quote_text == "你必须先相信某种回声。"
    assert epigraph.source_text == "《夜航西飞》 柏瑞尔·马卡姆"
    assert epigraph.raw_text == "你必须先相信某种回声。——《夜航西飞》 柏瑞尔·马卡姆\n"
    assert epigraph.end_offset == len(epigraph.raw_text)
    assert epigraph.quote == epigraph.quote_text
    assert epigraph.attribution == epigraph.source_text
    _assert_strip_semantics(text)


def test_detect_epigraph_same_line_author_book_format():
    text = "我走得很慢，但我从不后退。 鲁迅，《热风》\n\n正文开始。"

    epigraph = detect_epigraph(text)

    assert epigraph is not None
    assert epigraph.quote_text == "我走得很慢，但我从不后退。"
    assert epigraph.source_text == "鲁迅，《热风》"
    assert epigraph.raw_text == "我走得很慢，但我从不后退。 鲁迅，《热风》\n"
    assert epigraph.end_offset == len(epigraph.raw_text)
    _assert_strip_semantics(text)


def test_detect_epigraph_standalone_attribution():
    text = "所谓故乡，不过是祖先流浪的最后一站。\n— 木心，《哥伦比亚的倒影》\n\n这里是正文。"

    epigraph = detect_epigraph(text)

    assert epigraph is not None
    assert epigraph.quote_text == "所谓故乡，不过是祖先流浪的最后一站。"
    assert epigraph.source_text == "木心，《哥伦比亚的倒影》"
    assert epigraph.raw_text == "所谓故乡，不过是祖先流浪的最后一站。\n— 木心，《哥伦比亚的倒影》\n"
    assert epigraph.end_offset == len(epigraph.raw_text)
    _assert_strip_semantics(text)


def test_detect_epigraph_multiline_quote():
    text = (
        "世界微尘里，\n"
        "吾宁爱与憎。\n"
        "——《北青萝》 李商隐\n"
        "\n"
        "第一段正文。"
    )

    epigraph = detect_epigraph(text)

    assert epigraph is not None
    assert epigraph.quote_text == "世界微尘里，\n吾宁爱与憎。"
    assert epigraph.source_text == "《北青萝》 李商隐"
    assert epigraph.raw_text == "世界微尘里，\n吾宁爱与憎。\n——《北青萝》 李商隐\n"
    assert epigraph.end_offset == len(epigraph.raw_text)
    _assert_strip_semantics(text)


def test_detect_epigraph_preserves_crlf_offsets():
    text = "世界微尘里，吾宁爱与憎。\r\n——《北青萝》 李商隐\r\n\r\n正文。"

    epigraph = detect_epigraph(text)

    assert epigraph is not None
    assert epigraph.quote_text == "世界微尘里，吾宁爱与憎。"
    assert epigraph.source_text == "《北青萝》 李商隐"
    assert epigraph.raw_text == "世界微尘里，吾宁爱与憎。\r\n——《北青萝》 李商隐\r\n"
    assert text[: epigraph.end_offset] == epigraph.raw_text
    _assert_strip_semantics(text)


def test_detect_epigraph_requires_attribution():
    text = "世界微尘里，吾宁爱与憎。\n第一段正文。"

    assert detect_epigraph(text) is None
    assert strip_epigraph(text) == text


def test_detect_epigraph_does_not_misread_long_body_opening():
    text = (
        "清晨五点半，雨刚停，院墙外的车轮声在潮湿的石板路上拖出很长的回音。\n"
        "我摸黑起身，把昨夜没写完的信重新读了一遍，觉得每一句都像要离开。\n"
        "作者，《书名》\n"
        "\n"
        "后文。"
    )

    assert detect_epigraph(text) is None
    assert strip_epigraph(text) == text
