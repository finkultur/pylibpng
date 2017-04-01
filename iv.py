#!/usr/bin/python

import pygame, sys
import pylibpng

def show_png(surface, png):
    for h in range(0, png.height):
        for w in range(0, png.width):
            surface.fill(png.pixels[h][w], ((w,h), (1,1)))


if __name__ == '__main__':

    pygame.init()
    screen = pygame.display.set_mode((400,400))
    clock = pygame.time.Clock()
    screen.fill(pygame.Color(255,255,255))

    pic = pylibpng.PNG(sys.argv[1])
    show_png(screen, pic)

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
        pygame.display.update()
        clock.tick(30)

