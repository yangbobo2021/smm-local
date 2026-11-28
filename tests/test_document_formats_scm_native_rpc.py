"""Privileged test maintenance accepts only bounded, canonical task arguments."""
from pathlib import Path
import sys
import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts/acceptance'))
from document_formats_scm_native import cli_arguments


def test_read_output_is_single_canonical_direct_task_file(tmp_path):
    task=tmp_path/'task';task.mkdir()
    good=['documents','read','--reference','frozen-ref','--original-output',str(task/'raw.pdf')]
    assert cli_arguments(good,task)==good
    wrong=[
        ['documents','read','--reference','frozen-ref','--original-output='+str(tmp_path/'outside.pdf')],
        good+['--original-output',str(tmp_path/'outside.pdf')],
        good+['--original-output',str(task/'another.pdf')],
        ['documents','read','--reference','frozen-ref','--original-output',str(tmp_path/'outside.pdf')],
        ['documents','read','--reference','frozen-ref','--output',str(task/'raw.pdf')],
        ['documents','read','--reference','frozen-ref','--state-dir',str(task)],
        ['documents','refresh','--source-id','a'*32,'--source-id','b'*32],
    ]
    for args in wrong:
        with pytest.raises(AssertionError):cli_arguments(args,task)


def test_collection_and_retry_compare_values_are_bounded(tmp_path):
    task=tmp_path/'task';task.mkdir()
    args=['documents','add',str(task/'资料 空格/native-path.docx'),'--project-id','1']
    assert cli_arguments(args,task)==args
    with pytest.raises(AssertionError):cli_arguments(['documents','add',str(tmp_path/'other.docx'),'--project-id','1'],task)
    args=['documents','reprocess','--document-id','a'*32,'--capture-id','b'*32,'--expected-attempt-id','c'*32,'--expected-version','1','--expected-processing-version','1']
    assert cli_arguments(args,task)==args
    with pytest.raises(AssertionError):cli_arguments(args[:-2],task)


def test_reparse_task_root_cannot_select_privileged_output(tmp_path):
    task=tmp_path/'task';outside=tmp_path/'outside';outside.mkdir()
    try:task.symlink_to(outside,target_is_directory=True)
    except OSError:pytest.skip('host cannot create this link; Windows actual junction remains separate platform control')
    with pytest.raises(AssertionError):cli_arguments(['documents','read','--reference','frozen','--original-output',str(task/'raw.bin')],task)


def test_resume_scope_binds_parent_capture_and_worker_token():
    from document_formats_scm_native_guard import resume_task_matches
    aid='a'*32
    parent='smm_hub._archive.document_processing'
    for name in ('process','_process'):
        assert resume_task_matches(parent,name,{'attempt_id':aid},['service','run'],aid)
        assert not resume_task_matches(parent,name,{'attempt_id':'b'*32},['service','run'],aid)
        assert not resume_task_matches(parent,name,None,['service','run'],aid)
        assert not resume_task_matches(parent,name,{},['service','--task-token',aid],aid)
    for module,name in [('smm_hub._archive.document_formats.word','parse'),('smm_hub._archive.document_formats.pdf','intermediate'),('smm_hub._archive.document_formats.ocr','recognize')]:
        assert resume_task_matches(module,name,None,['worker','--task-token',aid],aid)
        assert not resume_task_matches(module,name,None,['worker','--task-token','b'*32],aid)
        assert not resume_task_matches(module,name,{'attempt_id':aid},['worker'],aid)
