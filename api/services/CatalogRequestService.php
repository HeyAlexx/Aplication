<?php
declare(strict_types=1);

final class CatalogRequestService
{
    private const FILE = 'catalog-solicitudes.json';
    private Closure $resolver;
    private Closure $authorize;
    private Closure $authorizeUser;

    public function __construct(private JsonStorage $storage, private CatalogService $catalog,
                                callable $resolver, callable $authorize, callable $authorizeUser)
    {
        $this->resolver = Closure::fromCallable($resolver);
        $this->authorize = Closure::fromCallable($authorize);
        $this->authorizeUser = Closure::fromCallable($authorizeUser);
    }

    private function admin(): array
    {
        $actor = ($this->authorize)();
        if (!($actor['isAuthenticated'] ?? false) || ($actor['role'] ?? '') !== 'admin') {
            throw new ApiException('Esta acción requiere un administrador.', 403);
        }
        return $actor;
    }

    public function all(): array
    {
        $this->admin();
        $rows = $this->storage->read(self::FILE);
        foreach ($rows as &$row) { unset($row['claim']); }
        unset($row);
        return array_reverse($rows);
    }

    public function favorite(array $session, string $id, array $client): void
    {
        $identity = ExternalCatalogService::identity($id);
        if (!(($session['isAuthenticated'] ?? false)) || ($session['id'] ?? '') === '') {
            throw new ApiException('Debe iniciar sesión.', 401);
        }
        if ((isset($client['source']) && $client['source'] !== $identity['source'])
            || (isset($client['id']) && $client['id'] !== $id)) {
            throw new ApiException('La identidad externa no coincide.');
        }
        if ($this->catalog->stored($id) !== null) {
            throw new ApiException('El contenido no está disponible.', 404);
        }
        $prior = $this->storage->read(self::FILE);
        $same = null;
        $pending = 0;
        foreach ($prior as $row) {
            if (($row['userId'] ?? '') !== $session['id']) { continue; }
            if (($row['contentId'] ?? '') === $id) { $same = $row; }
            if (in_array($row['status'] ?? '', ['pending','approving'],true)) { $pending++; }
        }
        if ($same === null && ($pending >= 20 || count($prior) >= 10000)) {
            throw new ApiException('Se alcanzó el límite de solicitudes pendientes.', 429);
        }
        if ($same === null) { $this->reserveResolution($session['id']); }
        $candidate = $same['candidate'] ?? ExternalCatalogService::snapshot($id, ($this->resolver)($id));
        $this->storage->transaction(function () use ($session,$id,$candidate): void {
            $currentUser = ($this->authorizeUser)();
            if (!($currentUser['isAuthenticated'] ?? false) || ($currentUser['id'] ?? '') !== $session['id']) {
                throw new ApiException('La sesión ya no permite esta operación.',401);
            }
            $current = $this->catalog->stored($id);
            if ($current !== null && ($current['status'] ?? '') === 'Oculto') {
                throw new ApiException('El contenido no está disponible.',404);
            }
            $rows = $this->storage->read(self::FILE);
            $found = null;
            $pending = 0;
            foreach ($rows as $i=>$row) {
                if (($row['userId'] ?? '') !== $session['id']) { continue; }
                if (($row['contentId'] ?? '') === $id) { $found = $i; }
                if (in_array($row['status'] ?? '', ['pending','approving'],true)) { $pending++; }
            }
            if ($found === null && $current === null) {
                if ($pending >= 20 || count($rows) >= 10000) { throw new ApiException('Se alcanzó el límite de solicitudes.',429); }
                $rows[] = ['id'=>'catalog-request-'.bin2hex(random_bytes(12)), 'contentId'=>$id,
                    'userId'=>$session['id'], 'requestedBy'=>$session['name'] ?? 'Usuario',
                    'candidate'=>$candidate, 'status'=>'pending', 'createdAt'=>date(DATE_ATOM)];
            } elseif ($found !== null && ($rows[$found]['status'] ?? '') === 'cancelled') {
                if ($pending >= 20) { throw new ApiException('Se alcanzó el límite de solicitudes pendientes.',429); }
                $rows[$found]['status'] = 'pending';
                $rows[$found]['updatedAt'] = date(DATE_ATOM);
            }
            $favorites = $this->storage->read('favoritos.json');
            $exists = array_filter($favorites, fn($f)=>($f['userId']??'')===$session['id'] && ($f['contentId']??'')===$id);
            if (!$exists) {
                $favorites[] = ['userId'=>$session['id'], 'contentId'=>$id,
                                'snapshot'=>$candidate, 'createdAt'=>date(DATE_ATOM)];
            }
            $this->storage->write(self::FILE,$rows);
            $this->storage->write('favoritos.json',$favorites);
        });
    }

    private function reserveResolution(string $userId): void
    {
        $this->storage->transaction(function () use ($userId): void {
            $now = time();
            $rows = array_values(array_filter($this->storage->read('catalog-resolutions.json'),
                fn($r) => (int)($r['expiresAt'] ?? 0) > $now));
            $userCount = count(array_filter($rows, fn($r) => ($r['userId'] ?? '') === $userId));
            if ($userCount >= 20 || count($rows) >= 200) {
                throw new ApiException('Se alcanzó el límite temporal de consultas externas. Inténtelo después.',429);
            }
            $rows[] = ['userId'=>$userId,'expiresAt'=>$now+900];
            $this->storage->write('catalog-resolutions.json',$rows);
        });
    }

    public function cancel(string $userId, string $id): void
    {
        // Caller holds the same private transaction as favorite removal.
        $rows = $this->storage->read(self::FILE);
        $changed = false;
        foreach ($rows as &$row) {
            if (($row['userId']??'')===$userId && ($row['contentId']??'')===$id && ($row['status']??'')==='pending') {
                $row['status']='cancelled'; $row['updatedAt']=date(DATE_ATOM); $changed=true;
            }
        }
        unset($row);
        if ($changed) { $this->storage->write(self::FILE,$rows); }
    }

    public function statuses(string $userId): array
    {
        $result=[];
        foreach ($this->storage->read(self::FILE) as $row) {
            if (($row['userId']??'')===$userId) { $result[$row['contentId']]=$row['status']; }
        }
        return $result;
    }

    public function decide(string $requestId, string $decision): array
    {
        $actor = $this->admin();
        if (!in_array($decision,['approve','reject'],true)) { throw new ApiException('Decisión inválida.'); }
        $claim = bin2hex(random_bytes(16));
        $request = $this->storage->transaction(function () use ($requestId,$decision,$actor,$claim): array {
            $this->admin();
            $rows = $this->storage->read(self::FILE);
            foreach ($rows as $index=>$row) {
                if (($row['id']??'')!==$requestId) { continue; }
                if (($row['status']??'') === 'approved' && $decision==='approve') { return $row; }
                if (($row['status']??'') === 'rejected' && $decision==='reject') { return $row; }
                if (!in_array($row['status']??'',['pending','approving'],true)) {
                    throw new ApiException('La solicitud ya no está pendiente.',409);
                }
                if (($row['status']??'')==='approving' && ($row['claim']['by']??'')!==$actor['id']
                    && (int)($row['claim']['expiresAt']??0)>time()) {
                    throw new ApiException('Otro administrador está procesando la solicitud.',409);
                }
                if ($decision==='reject') {
                    if ($this->catalog->stored($row['contentId'])!==null) {
                        throw new ApiException('El título ya fue incorporado; complete la aprobación.',409);
                    }
                    $row['status']='rejected';
                    $row['reviewedBy']=$actor['id']; $row['reviewedAt']=date(DATE_ATOM);
                    unset($row['claim']);
                } else {
                    $row['status']='approving';
                    $row['claim']=['token'=>$claim,'by'=>$actor['id'],'expiresAt'=>time()+300];
                }
                $rows[$index]=$row;
                $this->storage->write(self::FILE,$rows);
                return $row;
            }
            throw new ApiException('La solicitud no existe.',404);
        });
        if ($decision==='reject' || $request['status']==='approved') {
            unset($request['claim']); return $request;
        }
        try {
            $id=$request['contentId'];
            // Provider I/O is outside locks; never use the submitted snapshot as authority for publication.
            $candidate=ExternalCatalogService::snapshot($id,($this->resolver)($id));
            $imported=$this->catalog->importExternal($id,$candidate,function () use ($requestId,$claim): array {
                $actor=$this->admin(); // Fresh authorization at the actual catalog commit.
                $rows=$this->storage->read(self::FILE);
                foreach ($rows as $row) {
                    if (($row['id']??'')===$requestId && ($row['status']??'')==='approving'
                        && hash_equals((string)($row['claim']['token']??''),$claim)
                        && (int)($row['claim']['expiresAt']??0)>time()) { return $actor; }
                }
                throw new ApiException('La solicitud cambió; actualice la revisión.',409);
            });
            return $this->storage->transaction(function () use ($requestId,$claim,$actor,$imported): array {
                $rows=$this->storage->read(self::FILE);
                foreach ($rows as $index=>$row) {
                    if (($row['id']??'')!==$requestId) { continue; }
                    if (!hash_equals((string)($row['claim']['token']??''),$claim)) {
                        throw new ApiException('La aprobación se reanudó desde otra petición.',409);
                    }
                    $row['status']='approved'; $row['candidate']=$imported;
                    $row['reviewedBy']=$actor['id']; $row['reviewedAt']=date(DATE_ATOM);
                    unset($row['claim']);
                    $rows[$index]=$row; $this->storage->write(self::FILE,$rows);
                    return $row;
                }
                throw new ApiException('No se pudo finalizar la aprobación; reintente.',409);
            });
        } catch (Throwable $error) {
            // If catalog commit already happened, keep the recoverable claim for an idempotent retry.
            $published=$this->catalog->stored($request['contentId'])!==null;
            if (!$published) {
                $this->storage->transaction(function () use ($requestId,$claim): void {
                    $rows=$this->storage->read(self::FILE);
                    foreach ($rows as &$row) {
                        if (($row['id']??'')===$requestId && hash_equals((string)($row['claim']['token']??''),$claim)) {
                            $row['status']='pending'; unset($row['claim']);
                        }
                    }
                    unset($row); $this->storage->write(self::FILE,$rows);
                });
            }
            throw $error;
        }
    }
}

