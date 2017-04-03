#!/usr/bin/python

import pygame, sys
import pylibpng

def show_png(surface, png, zoom=1):
    for h in range(0, png.height):
        for w in range(0, png.width):
            surface.fill(png.pixels[h][w], ((w*zoom,h*zoom), (zoom,zoom)))

if __name__ == '__main__':

    pygame.init()

    pic = pylibpng.PNG(sys.argv[1])
    black = (255,255,255)

    screen = pygame.display.set_mode((pic.width,pic.height))
    clock = pygame.time.Clock()
    
    if pic.bkgd:
        screen.fill(pic.bkgd)
    else:
        screen.fill(black)

    show_png(screen, pic, 1)

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
        pygame.display.update()
        clock.tick(30)

