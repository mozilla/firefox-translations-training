

dag:
	snakemake --dag | dot -Tpdf > dag.pdf

run-with-monitor:
	snakemake \
	  --use-conda \
	  --cores all \
	  --wms-monitor http://127.0.0.1:5000