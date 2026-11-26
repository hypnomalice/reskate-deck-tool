"""Packaged-app check: load/save through the editor, then use its normal exporter."""
from pathlib import Path
import json,hashlib,traceback

def check(request):
    options=json.loads(Path(request).read_text());report=Path(options['report']);report.parent.mkdir(parents=True,exist_ok=True)
    try:
        from unittest.mock import patch
        from qt_ui import Creator,application
        from app_version import APP_VERSION
        import layer_finish,native_export,creator_engine
        app=application()
        with patch.object(Creator,'check_updates',lambda self:None):window=Creator()
        window.load_project(options['project']);project=window.workspace()
        assert layer_finish.enabled(project['decks'][0])
        assert project['decks'][0]['layer_finishes']['foreground']['finish']=='normal'
        assert project['decks'][0]['layer_finishes']['background']['finish']=='holographic'
        saved=report.with_name('Tool round-trip project.json');saved.write_text(json.dumps(project,indent=2)+'\n')
        window.load_project(saved);again=window.workspace();assert project==again
        window.preview_timer.stop();window.poll_timer.stop();window.animation_timer.stop();window.baseline=again;window.close()
        # Export itself checks the recognition strip before writing content.
        native_export.export_zip(again['decks'],options['destination'],title=options['title'],author='IdolRiot',game_root=options['game_root'],compiler=options['compiler'])
        output=Path(options['destination'])
        data=dict(ok=True,tool_version=APP_VERSION,normal_editor_load_save=True,normal_export_path=True,private_export_patches=False,project=str(saved),zip=str(output),bytes=output.stat().st_size,sha256=hashlib.sha256(output.read_bytes()).hexdigest(),minimum_sdec=layer_finish.MINIMUM_CORE,game_launched=False)
        report.write_text(json.dumps(data,indent=2)+'\n')
    except Exception:
        report.write_text(json.dumps(dict(ok=False,error=traceback.format_exc()),indent=2)+'\n');raise
