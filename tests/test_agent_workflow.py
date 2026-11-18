from scripts.agent_workflow import regress, junit
import pytest


def test_regression_summary_keeps_failures_missing_and_skips_distinct(tmp_path):
    baseline = tmp_path / "base.xml"
    current = tmp_path / "current.xml"
    baseline.write_text('<testsuite><testcase classname="a" name="one"/><testcase classname="a" name="gone"/></testsuite>')
    current.write_text('<testsuite><testcase classname="a" name="one"><failure message="wrong amount"/></testcase><testcase classname="a" name="skip"><skipped/></testcase><testcase classname="a" name="err"><error/></testcase></testsuite>')
    report = regress(current, baseline, limit=1)
    assert report["counts"] == {"passed":0,"failure":1,"error":1,"skipped":1}
    assert report["failures"][0]["baseline"] == "passed"
    assert report["failures_omitted"] == 1
    assert report["missing_from_current"] == ["a::gone"]


@pytest.mark.parametrize("xml", ['<testsuite/>', '<testsuite><testcase name="same"/><testcase name="same"/></testsuite>'])
def test_ambiguous_or_empty_reports_are_rejected(tmp_path, xml):
    path = tmp_path / "report.xml"
    path.write_text(xml)
    with pytest.raises(ValueError):
        junit(path)
