import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import production_history as history
from storage_transaction import atomic_json
from sync_anime_workbook import raw_row,make_new_record


class ScopedProductionHistoryTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='altoidss-scoped-production-')
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.workspace=self.root/'workspace'
        production=self.workspace/'ProyectoFinal/Aplication'
        self.catalog=self.workspace/'datos/produccion/catalogo'
        state=self.catalog.parent/'anime-sync'
        for directory in (production/'data',self.catalog,state): directory.mkdir(parents=True)
        atomic_json(production/'data/usuarios.json',[])
        atomic_json(production.parent/'catalog-storage.local.json',{'environment':'produccion','catalogDir':str(self.catalog),'syncStateDir':str(state)})
        self.rows=[raw_row(2,('01','Old first','Finalizado','Serie',12,1,'S01','Visto',2020,1)),
                   raw_row(3,('02','Old second','Finalizado','Serie',12,1,'S01','Visto',2021,2))]
        self.old=[{'id':'old-'+row['sourceCode'],'sourceCode':row['sourceCode'],'sourceRow':row['row'],'title':row['title'],
                   'createdAt':'2026-08-24T00:00:00-06:00'} for row in self.rows]
        self.local={'id':'local','title':'Local real app date','createdAt':'2026-10-19T12:00:00-06:00'}
        new_row=raw_row(4,('03','New batch','Emision','Serie',0,1,'S01','Por Ver',2027,1))
        self.new=make_new_record(new_row,'2026-10-19T13:21:37-06:00')
        self.before=[*self.old,self.local,self.new]
        for name in ('anime.json','anime-hoja.json','peliculas.json','series.json','noticias.json','temporadas.json','episodios.json','anime-revisiones.json','anime-sheet-writeback.json'):
            atomic_json(self.catalog/name,self.before if name=='anime.json' else [*self.rows,new_row] if name=='anime-hoja.json' else [])
        atomic_json(state/'state.json',{'sourceHash':'unchanged-fixture'})
        snapshot=self.workspace/'work/preproduction-snapshots/before-approved-deploy'
        self.baseline=snapshot/'production-central/catalogo/anime.json'
        mirror=self.baseline.parent/'anime-hoja.json'
        atomic_json(self.baseline,[*self.old,self.local])
        atomic_json(mirror,self.rows)
        atomic_json(snapshot/'manifest.json',{'copies':[{'source':str(self.catalog/path.name),'backup':str(path),
                    'sha256':history.digest(path.read_bytes())} for path in (self.baseline,mirror)]})

    def plan(self):
        output,plan=history.prepare(self.workspace,self.baseline,2)
        plan_path=output/'plan.json'
        return plan_path,history.digest(plan_path.read_bytes())

    def test_scoped_apply_and_retry_preserve_later_batch_locals_and_other_data(self):
        plan,sha=self.plan()
        before_hashes=history.protected_hashes(self.workspace,self.workspace/'ProyectoFinal/Aplication')
        backup=self.root/'independent-backup'
        result=history.apply(self.workspace,plan,sha,backup)
        self.assertEqual(result['status'],'APPLIED')
        after=json.loads((self.catalog/'anime.json').read_bytes())
        self.assertEqual(after[-2:],[self.local,self.new])
        self.assertTrue(all(item.get('historicalOrderInitialization') for item in after[:2]))
        self.assertTrue(all(item['historicalOrderInitialization']['originalDates']['createdAt']==self.old[0]['createdAt'] for item in after[:2]))
        self.assertEqual(history.apply(self.workspace,plan,sha,backup)['status'],'already-initialized')
        current_hashes=history.protected_hashes(self.workspace,self.workspace/'ProyectoFinal/Aplication')
        current_hashes[str(self.catalog/'anime.json')]=before_hashes[str(self.catalog/'anime.json')]
        self.assertEqual(current_hashes,before_hashes)
        self.assertEqual(json.loads((backup/'datos/produccion/catalogo/anime.json').read_bytes()),self.before)

    def test_wrong_approval_sha_and_stale_current_data_refuse_live_write(self):
        plan,sha=self.plan()
        with self.assertRaisesRegex(ValueError,'aprobación'):
            history.apply(self.workspace,plan,'wrong',self.root/'never-written')
        changed=copy.deepcopy(self.before)
        changed[-1]['title']='new external edit'
        atomic_json(self.catalog/'anime.json',changed)
        with self.assertRaisesRegex(ValueError,'cambió'):
            history.apply(self.workspace,plan,sha,self.root/'never-written')
        self.assertEqual(json.loads((self.catalog/'anime.json').read_bytes()),changed)
        self.assertFalse((self.root/'never-written').exists())

    def test_source_row_changes_refuse_preview(self):
        mirror=json.loads((self.catalog/'anime-hoja.json').read_bytes())
        mirror[0]['row']=20
        atomic_json(self.catalog/'anime-hoja.json',mirror)
        with self.assertRaisesRegex(ValueError,'filas históricas cambiaron'):
            self.plan()

    def test_baseline_tampering_and_development_source_are_rejected(self):
        atomic_json(self.baseline,[])
        with self.assertRaisesRegex(ValueError,'manifiesto'):
            self.plan()
        with self.assertRaisesRegex(ValueError,'snapshot previo de producción'):
            history.prepare(self.workspace,self.workspace/'Desarrollo/Aplication/data/anime.json',2)

    def test_later_real_batch_cannot_be_migrated_as_legacy(self):
        changed=copy.deepcopy(self.before)
        changed[0].update(sheetImportBatchId='sheet-real-batch',incorporationDateBasis='initial-sheet-sync')
        atomic_json(self.catalog/'anime.json',changed)
        with self.assertRaisesRegex(ValueError,'altas posteriores protegidas'):
            self.plan()

    def test_existing_orphan_reference_is_preserved_like_local_record(self):
        self.local.update(sourceCode='orphan-old-code',sourceRow=277)
        self.before[-2]=copy.deepcopy(self.local)
        atomic_json(self.catalog/'anime.json',self.before)
        atomic_json(self.baseline,[*self.old,self.local])
        manifest_path=self.baseline.parents[2]/'manifest.json'
        manifest=json.loads(manifest_path.read_bytes())
        manifest['copies'][0]['sha256']=history.digest(self.baseline.read_bytes())
        atomic_json(manifest_path,manifest)
        plan,sha=self.plan()
        result=history.apply(self.workspace,plan,sha,self.root/'independent-orphan-backup')
        self.assertEqual(result['localRecordsUnchanged'],1)
        self.assertEqual(result['laterBatchRecordsUnchanged'],1)
        self.assertEqual(json.loads((self.catalog/'anime.json').read_bytes())[-2],self.local)

    def test_implementation_fingerprint_is_required_before_live_write(self):
        plan,sha=self.plan()
        payload=json.loads(plan.read_bytes())
        payload['implementationSha256']['tools/production_history.py']='0'*64
        atomic_json(plan,payload)
        with self.assertRaisesRegex(ValueError,'implementación cambió'):
            history.apply(self.workspace,plan,history.digest(plan.read_bytes()),self.root/'never-written')
        self.assertEqual(json.loads((self.catalog/'anime.json').read_bytes()),self.before)


if __name__=='__main__':
    unittest.main()
