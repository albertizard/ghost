CFLAGS = -O4 -Wall
CC = /usr/local/bin/gcc-5 -std=gnu99

all: ghmock.o band_spec.o
	$(CC) ghmock.o band_spec.o -lm -lgsl -lgslcblas -lgomp -o ghmock

ghmock.o: ghmock.c
	$(CC) -O4 -fopenmp -DSTANDALONE -c ghmock.c

band_spec.o: band_spec.c
	$(CC) -O4 -fopenmp -DSTANDALONE -c band_spec.c

python:
	python setup.py build_ext --inplace

clean:
	rm -f *.o
	rm -f ghost.so
	rm -rf build/
