import configparser
from hedgepig_logger import log
from .. import nn_io
from ..data_models import *
from ..database import EmbeddingNeighborhoodDatabase

def loadAggregateNeighbors(src, trg, config, db, k=10):
    log.writeln('  >> Loading pre-calculated aggregate nearest neighbors')
    aggregate_neighbors = nn_io.loadPairedNeighbors(
        src, None, trg, config, k, aggregate=True, with_distances=True
    )

    log.writeln('  >> Adding to database')
    nbrs = []
    for (key, nbr_list) in aggregate_neighbors.items():
        for (nbr_key, dist) in nbr_list:
            nbrs.append(AggregateNearestNeighbor(
                source=src,
                target=trg,
                key=key,
                neighbor_key=nbr_key,
                mean_distance=dist
            ))
    db.insertOrUpdate(nbrs)


if __name__ == '__main__':
    def _cli():
        import optparse
        parser = optparse.OptionParser(usage='Usage: %prog')
        parser.add_option('-s', '--src', dest='src',
            help='(required) source specifier')
        parser.add_option('-t', '--trg', dest='trg',
            help='(required) target specifier')
        parser.add_option('-c', '--config', dest='configf',
            default='config.ini')
        parser.add_option('-k', '--nearest-neighbors', dest='k',
            help='number of nearest neighbors to use in statistics (default: %default)',
            type='int', default=5)
        parser.add_option('-l', '--logfile', dest='logfile',
            help='name of file to write log contents to (empty for stdout)',
            default=None)
        (options, args) = parser.parse_args()
        if not options.src:
            parser.print_help()
            parser.error('Must provide --src')
        if not options.trg:
            parser.print_help()
            parser.error('Must provide --trg')
        return options

    options = _cli()
    log.start(options.logfile)
    log.writeConfig([
        ('Source specifier', options.src),
        ('Target specifier', options.trg),
        ('Configuration file', options.configf),
        ('Number of nearest neighbors to add to DB', options.k),
    ], 'Loading aggregate neighbors into DB')

    log.writeln('Reading configuration file from %s...' % options.configf)
    config = configparser.ConfigParser()
    config.read(options.configf)
    config = config['PairedNeighborhoodAnalysis']
    log.writeln('Done.\n')

    log.writeln('Loading embedding neighborhood database...')
    db = EmbeddingNeighborhoodDatabase(config['DatabaseFile'])
    log.writeln('Database ready.\n')

    log.writeln('Loading aggregate {0}/{1} neighbors into database...'.format(options.src, options.trg))
    loadAggregateNeighbors(
        options.src,
        options.trg,
        config,
        db,
        k=options.k
    )
    log.writeln('Done.')

    log.stop()