from flask import Flask
from flask import render_template
from flask import request
from flask import jsonify
from flask import send_from_directory
app = Flask(__name__)

import os
import configparser
from nearest_neighbors.database import *
from nearest_neighbors.dashboard import packaging
from nearest_neighbors.dashboard import visualization

config = configparser.ConfigParser()
config.read('config.ini')

@app.route('/')
def landingPage():
    return send_from_directory('diachronic-concept-viewer/public', 'index.html')

@app.route('/<path:path>')
def staticFiles(path):
    return send_from_directory('diachronic-concept-viewer/public', path)

@app.route('/showchanges', methods=['POST'])
@app.route('/showchanges/<src>/<trg>/<filter_set>/<at_k>', methods=['GET', 'POST'])
def showChanges(src=None, trg=None, filter_set=None, at_k=None):
    if request.method == 'GET':
        getter = request.args.get
    else:
        getter = request.form.get

    if src is None:
        src = getter('src', None)
    if trg is None:
        trg = getter('trg', None)
    if filter_set is None:
        filter_set = getter('filter_set', None)
    if at_k is None:
        at_k = getter('at_k', None)

    db = EmbeddingNeighborhoodDatabase(config['PairedNeighborhoodAnalysis']['DatabaseFile'])

    top_cwd, bottom_cwd = [], []
    rows = db.selectFromEntityOverlapAnalysis(
        src,
        trg,
        filter_set,
        at_k,
        source_confidence_threshold=0.5,
        target_confidence_threshold=0.5,
        order_by='ConfidenceWeightedDelta DESC',
        limit=50
    )
    for row in rows:
        top_cwd.append({
            'Key': row.key,
            'String': row.string,
            'SourceConfidence': packaging.prettify(row.source_confidence, decimals=2),
            'TargetConfidence': packaging.prettify(row.target_confidence, decimals=2),
            'ENSimilarity': packaging.prettify(row.EN_similarity, decimals=2),
            'CWD': packaging.prettify(row.CWD, decimals=2)
        })

    rows = db.selectFromEntityOverlapAnalysis(
        src,
        trg,
        filter_set,
        at_k,
        source_confidence_threshold=0.5,
        target_confidence_threshold=0.5,
        order_by='ConfidenceWeightedDelta',
        limit=10
    )
    for row in rows:
        bottom_cwd.append({
            'Key': row.key,
            'String': row.string,
            'SourceConfidence': packaging.prettify(row.source_confidence, decimals=2),
            'TargetConfidence': packaging.prettify(row.target_confidence, decimals=2),
            'ENSimilarity': packaging.prettify(row.EN_similarity, decimals=2),
            'CWD': packaging.prettify(row.CWD, decimals=2)
        })

    db.close()

    return render_template(
        'showchanges.html',
        top_cwd=top_cwd,
        bottom_cwd=bottom_cwd,
        src=src,
        trg=trg
    )


@app.route('/info', methods=['POST'])
@app.route('/info/<query_key>', methods=['GET', 'POST'])
def info(query_key=None):
    if request.method == 'GET':
        getter = request.args.get
        lgetter = lambda key,default: request.args.get(key, default).split(',')
    else:
        getter = request.form.get
        lgetter = lambda key, default: request.form.getlist(key)

    if query_key is None:
        query_key = getter('query_key', None)
    
    neighbor_type = getter('neighbor_type', 'ENTITY')
    neighbor_type = EmbeddingType.parse(neighbor_type)

    db = EmbeddingNeighborhoodDatabase(config['PairedNeighborhoodAnalysis']['DatabaseFile'])
    corpora = config['PairedNeighborhoodAnalysis']['CorpusOrdering'].split(',')
    hc_threshold = float(config['PairedNeighborhoodAnalysis']['HighConfidenceThreshold'])
    num_neighbors = int(config['PairedNeighborhoodAnalysis']['NumNeighborsToShow'])

    ## (1) get its confidence history
    confidences = getConfidences(
        db,
        corpora,
        query_key
    )

    ## (2) get the nearest neighbors
    tables = getNeighborTables(
        db,
        corpora,
        query_key,
        neighbor_type,
        confidences,
        limit=num_neighbors,
        high_confidence_threshold=hc_threshold
    )

    ## (3) get the terms and definitions for the entity
    term_list, preferred_term = getTerms(
        db,
        query_key
    )
    definition_list = getDefinitions(
        db,
        query_key
    )

    ## (4) get its change history
    cwds = []
    for i in range(len(corpora)-1):
        change_src = corpora[i]
        change_trg = corpora[i+1]
        filter_set = '.HC_Union_{0}_{1}'.format(change_src, change_trg)  ## TODO HARD CODED
        at_k = 5  ## TODO HARD CODED

        rows = db.selectFromEntityOverlapAnalysis(
            change_src,
            change_trg,
            filter_set=filter_set,
            at_k=at_k,
            entity_key=query_key
        )
        rows = list(rows)
        if len(rows) == 1:
            cwds.append(rows[0].CWD)
        else:
            cwds.append(None)

    entity_change_analysis_base64 = packaging.renderImage(
        visualization.entityChangeAnalysis,
        args=(corpora, cwds),
        kwargs={'figsize': (11,3), 'font_size': 14}
    )

    confidence_analysis_base64 = packaging.renderImage(
        visualization.internalConfidenceAnalysis,
        args=(corpora, [confidences.get(c, None) for c in corpora], hc_threshold),
        kwargs={'figsize': (6,2), 'font_size': 14}
    )

    return render_template(
        'info.html',
        query_key=query_key,
        preferred_term=preferred_term,
        all_terms=sorted(term_list),
        all_definitions=sorted(definition_list),
        tables=tables,
        entity_change_analysis_base64=entity_change_analysis_base64,
        confidence_analysis_base64=confidence_analysis_base64
    )


@app.route('/terms', methods=['POST'])
@app.route('/terms/<query_key>', methods=['GET', 'POST'])
def terms(query_key=None):
    if request.method == 'GET':
        getter = request.args.get
    else:
        getter = request.form.get

    if query_key is None:
        query_key = getter('query_key', None)

    db = EmbeddingNeighborhoodDatabase(config['PairedNeighborhoodAnalysis']['DatabaseFile'])

    rows = db.selectFromEntityTerms(
        query_key
    )

    table_rows = []
    for row in rows:
        table_rows.append({
            'Term': row.term,
            'Preferred': ('X' if row.preferred == 1 else '')
        })

    return render_template(
        'terms.html',
        rows=table_rows
    )


@app.route('/search', methods=['POST'])
@app.route('/search/<query>', methods=['GET', 'POST'])
def search(query=None):
    if request.method == 'GET':
        getter = request.args.get
    else:
        getter = request.form.get

    if query is None:
        query = getter('query', None)

    db = EmbeddingNeighborhoodDatabase(config['PairedNeighborhoodAnalysis']['DatabaseFile'])

    rows = db.searchInEntityTerms(
        query
    )

    table_rows = []
    for row in rows:
        table_rows.append({
            'Key': row.entity_key,
            'Term': row.term,
        })

    return render_template(
        'search.html',
        query=query,
        rows=table_rows,
        corpora='2020-03-27,2020-04-03'  ## hard-coded value for now
    )


@app.route('/_get_aggregate_nearest_neighbors_membership')
def getAggregateNearestNeighborsMembership():
    query_key = request.args.get('query_key', None)
    current_corpora = request.args.get('current_corpora', '')

    current_corpora = set(current_corpora.split(','))

    db = EmbeddingNeighborhoodDatabase(config['PairedNeighborhoodAnalysis']['DatabaseFile'])

    rows = db.findAggregateNearestNeighborsMembership(query_key)

    table_rows = []
    for row in sorted(rows):
        table_rows.append({
            'Source': row,
            'Checked': 1 if row in current_corpora else 0
        })

    return jsonify(table_rows)


@app.route('/pairwise', methods=['POST'])
@app.route('/pairwise/<query>/<target>', methods=['GET', 'POST'])
def pairwise(query=None, target=None):
    if request.method == 'GET':
        getter = request.args.get
    else:
        getter = request.form.get

    if query is None:
        query = getter('query', None)
    if target is None:
        target = getter('target', None)

    db = EmbeddingNeighborhoodDatabase(config['PairedNeighborhoodAnalysis']['DatabaseFile'])
    num_neighbors = int(config['PairedNeighborhoodAnalysis']['NumNeighborsToShow'])

    ## (1) get pairwise similarity data
    rows = db.selectFromAggregatePairwiseSimilarity(query, target)
    rows = sorted(rows, key=lambda item: item.source)
    corpora, means, stds = [], [], []
    for row in rows:
        corpora.append(row.source)
        means.append(row.mean_similarity)
        stds.append(row.std_similarity)

    ## (2) get terms for each entity
    query_term_list, query_preferred_term = getTerms(
        db,
        query
    )
    target_term_list, target_preferred_term = getTerms(
        db,
        target
    )

    ## (3) get neighbors for each entity
    corpora = config['PairedNeighborhoodAnalysis']['CorpusOrdering'].split(',')
    neighbor_type = EmbeddingType.parse('ENTITY')
    query_confidences = getConfidences(
        db,
        corpora,
        query
    )
    target_confidences = getConfidences(
        db,
        corpora,
        target
    )
    query_tables = getNeighborTables(
        db,
        corpora,
        query,
        neighbor_type,
        query_confidences,
        limit=num_neighbors,
    )
    target_tables = getNeighborTables(
        db,
        corpora,
        target,
        neighbor_type,
        target_confidences,
        limit=num_neighbors,
    )

    ## (4) reconfigure table layout to have paired columnar browsing
    paired_tables = []
    for i in range(len(query_tables)):
        query_tables[i]['IsGridRowStart'] = True
        query_tables[i]['IsGridRowEnd'] = False

        target_tables[i]['IsGridRowStart'] = False
        target_tables[i]['IsGridRowEnd'] = True

        paired_tables.append(query_tables[i])
        paired_tables.append(target_tables[i])

    ## (5) draw the pairwise similarity graph
    pairwise_similarity_analysis_base64 = packaging.renderImage(
        visualization.pairwiseSimilarityAnalysis,
        args=(corpora, means, stds),
        kwargs={'figsize': (13,3), 'font_size': 14}
    )

    return render_template(
        'pairwise.html',
        query=query,
        query_preferred_term=query_preferred_term,
        query_terms=sorted(query_term_list),
        target=target,
        target_preferred_term=target_preferred_term,
        target_terms=sorted(target_term_list),
        paired_tables=paired_tables,
        pairwise_similarity_analysis_base64=pairwise_similarity_analysis_base64
    )




## TODO: change to single query
def getNeighborTables(db, corpora, query_key, neighbor_type, confidences,
        limit=10, high_confidence_threshold=0.5):
    tables = []
    TABLES_PER_ROW = 3
    for i in range(len(corpora)):
        corpus = corpora[i]
        filter_set='.HC_{0}'.format(corpus)
        rows = db.selectFromAggregateNearestNeighbors(
            corpus,
            corpus,
            filter_set,
            query_key,
            neighbor_type=neighbor_type,
            limit=limit
        )

        table_rows = []
        for row in rows:
            table_rows.append({
                'QueryKey': query_key,
                'NeighborKey': row.neighbor_key,
                'NeighborString': row.neighbor_string,
                'Distance': packaging.prettify(row.mean_distance, decimals=3)
            })

        confidence = confidences.get(corpus, None)
        if confidence is None:
            confidence = '--'
            table_class = 'no_data'
        else:
            if confidence >= high_confidence_threshold:
                table_class = 'high_confidence'
            else:
                table_class = 'low_confidence'
            confidence = packaging.prettify(confidence)

        tables.append({
            'Corpus': corpus,
            'Confidence': confidence,
            'Class': table_class,
            'Rows': table_rows,
            'NumRows' : limit,
            'IsGridRowStart': (i % TABLES_PER_ROW) == 0,
            'IsGridRowEnd': (i % TABLES_PER_ROW) == (TABLES_PER_ROW - 1),
        })
    return tables

## TODO: change to single query
def getConfidences(db, corpora, query_key):
    confidences = {}
    for corpus in corpora:
        rows = db.selectFromInternalConfidence(
            src=corpus,
            at_k=5,
            key=query_key
        )
        for row in rows:
            confidences[corpus] = row.confidence
    return confidences

def getTerms(db, query_key):
    all_terms = db.selectFromEntityTerms(
        query_key
    )
    term_list, preferred_term = [], ''
    for term in all_terms:
        if term.preferred == 1:
            preferred_term = term.term
        else:
            term_list.append(term.term)
    return term_list, preferred_term

def getDefinitions(db, query_key):
    all_definitions = db.selectFromEntityDefinitions(
        query_key
    )
    return [
        defn.definition
            for defn in all_definitions
    ]
