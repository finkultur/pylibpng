#!/usr/bin/python

import pygame, sys
import pylibpng

def show_png(surface, png, zoom=1):
    for h in range(0, png.height):
        for w in range(0, png.width):
            try:
                surface.fill(png.pixels[h][w], ((w*zoom,h*zoom), (zoom,zoom)))
            except IndexError:
                print("%i, %i" % (h,w))

if __name__ == '__main__':
    if len(sys.argv) == 3:
        zoom = int(sys.argv[2])
    else:
        zoom = 1
    pic = pylibpng.PNG(sys.argv[1])
    black = (0,0,0)

    pygame.init()
    screen = pygame.display.set_mode((pic.width*zoom,pic.height*zoom), pygame.RESIZABLE)
    clock = pygame.time.Clock()
    
    if pic.bkgd:
        screen.fill(pic.bkgd)
    else:
        screen.fill(black)

    show_png(screen, pic, zoom)
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_PLUS:
                    zoom += 1
                    show_png(screen, pic, zoom)
                elif event.key == pygame.K_MINUS:
                    if zoom > 1:
                        zoom -= 1
                        show_png(screen, pic, zoom)
            elif event.type == pygame.VIDEORESIZE:
                screen = pygame.display.set_mode((event.w, event.h), pygame.RESIZABLE)
                screen.fill(black)
                show_png(screen, pic, zoom)
        pygame.display.update()
        clock.tick(30)

